from datetime import UTC, datetime
from enum import Enum

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    """User roles enum."""

    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class UserBase(SQLModel):
    """Base user model with common fields."""

    email: EmailStr = Field(unique=True, index=True)
    is_active: bool = True
    role: UserRole = UserRole.USER


class User(UserBase, table=True):
    """User database model."""

    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserRead(UserBase):
    """User read model for API responses."""

    id: int

    class Config:
        from_attributes = True


class UserCreate(UserBase):
    """User creation model."""

    password: str


class UserUpdate(SQLModel):
    """User update model."""

    email: str | None = None
    is_active: bool | None = None
    role: UserRole | None = None
    password: str | None = None


class UserLogin(SQLModel):
    """User login model."""

    email: str
    password: str

