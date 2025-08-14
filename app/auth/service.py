from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import HTTPException, status
from jose import jwt
from sqlmodel import Session, select

from app.settings import settings
from app.user.models import User, UserCreate


class AuthService:
    """Authentication service for JWT and password operations."""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except Exception:
            return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Generate password hash."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @classmethod
    async def create_user(cls, session: Session, user_create: UserCreate) -> User:
        """Create a new user."""
        statement = select(User).where(User.email == user_create.email)
        existing_user = session.exec(statement).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        hashed_password = cls.get_password_hash(user_create.password)
        user = User(
            email=user_create.email,
            hashed_password=hashed_password,
            role=user_create.role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    async def authenticate_user(self, email: str, password: str) -> User:
        """Authenticate a user with email and password."""
        statement = select(User).where(User.email == email)
        user = self.session.exec(statement).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not self.verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    def create_access_token(
        self, data: dict, expires_delta: timedelta | None = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

