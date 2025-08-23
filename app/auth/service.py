from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import HTTPException, status
from uuid import UUID as UUIDType
from jose import jwt
from sqlmodel import Session, select

from app.db_models import Manager, Player, Team
from app.settings import settings


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
        salt = bcrypt.gensalt(rounds=10)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @classmethod
    async def create_manager(cls, session: Session, payload: dict) -> Manager:
        """Create a new manager account in managers table."""
        # Uniqueness checks
        existing_email = session.exec(
            select(Manager).where(Manager.email == payload["email"])  
        )
        if existing_email.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        if payload.get("squad_name"):
            existing_squad = session.exec(
                select(Manager).where(Manager.squad_name == payload["squad_name"]) 
            )
            if existing_squad.first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Squad name already taken",
                )

        # Validate optional favorites; ignore if not existing
        fav_team_id = payload.get("fav_team")
        if fav_team_id is not None and not session.get(Team, fav_team_id):
            fav_team_id = None

        # Handle fav_player which is now a UUID PK.
        # Treat 0/"0"/None/empty as no favorite, otherwise try to coerce to UUID and validate existence.
        fav_player_raw = payload.get("fav_player")
        fav_player_id = None
        if fav_player_raw not in (None, 0, "0", "", "null"):
            try:
                fav_player_uuid = UUIDType(str(fav_player_raw))
                if session.get(Player, fav_player_uuid):
                    fav_player_id = fav_player_uuid
            except (ValueError, TypeError):
                fav_player_id = None

        # Parse birthdate if provided
        bd_raw = payload.get("birthdate")
        birthdate = None
        if isinstance(bd_raw, str) and bd_raw.strip():
            try:
                # Try ISO format first (YYYY-MM-DD)
                birthdate = datetime.fromisoformat(bd_raw)
            except ValueError:
                try:
                    # Try MM/DD/YYYY format
                    from datetime import datetime as dt
                    birthdate = dt.strptime(bd_raw, "%m/%d/%Y")
                except ValueError:
                    try:
                        # Try DD/MM/YYYY format
                        birthdate = dt.strptime(bd_raw, "%d/%m/%Y")
                    except ValueError:
                        # If all parsing fails, leave as None
                        birthdate = None
        elif isinstance(bd_raw, datetime):
            birthdate = bd_raw

        hashed_password = cls.get_password_hash(payload["password"])
        manager = Manager(
            manager_id=None,
            mng_firstname=payload.get("firstname", ""),
            mng_lastname=payload.get("lastname", ""),
            squad_name=payload.get("squad_name", ""),
            email=payload["email"],
            hashed_password=hashed_password,
            birthdate=birthdate,
            city=payload.get("city"),
            fav_team_id=fav_team_id,
            fav_player_id=fav_player_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            mng_datapoint="",
            wallet=payload.get("wallet", 100),
        )
        session.add(manager)
        session.commit()
        session.refresh(manager)
        return manager

    async def authenticate_manager(self, email: str, password: str) -> Manager:
        """Authenticate a manager using managers table."""
        statement = select(Manager).where(Manager.email == email)
        manager = self.session.exec(statement).first()

        if not manager:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not self.verify_password(password, manager.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return manager

    def create_access_token(
        self, data: dict, expires_delta: timedelta | None = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            # Default: 7 days if not configured
            minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7)
            expire = datetime.now(UTC) + timedelta(minutes=minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

