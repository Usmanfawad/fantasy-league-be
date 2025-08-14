from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.auth.service import AuthService
from app.user.models import User, UserCreate, UserUpdate


class UserService:
    """Service for user management operations."""

    def __init__(self, session: Session):
        self.session = session
        self.auth_service = AuthService(session)

    def get_user_by_id(self, user_id: int) -> User | None:
        """Get user by ID."""
        return self.session.get(User, user_id)

    def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()

    def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get list of users with pagination."""
        statement = select(User).offset(skip).limit(limit)
        return self.session.exec(statement).all()

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        if self.get_user_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        db_user = User(
            email=user_data.email,
            role=user_data.role,
            hashed_password=self.auth_service.get_password_hash(user_data.password),
        )

        self.session.add(db_user)
        self.session.commit()
        self.session.refresh(db_user)
        return db_user

    def update_user(self, user_id: int, user_data: UserUpdate) -> User | None:
        """Update user data."""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        update_data = user_data.model_dump(exclude_unset=True)

        if "password" in update_data:
            update_data["hashed_password"] = self.auth_service.get_password_hash(
                update_data.pop("password")
            )

        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.now(UTC)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        self.session.delete(user)
        self.session.commit()
        return True

