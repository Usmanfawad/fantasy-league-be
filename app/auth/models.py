from datetime import datetime

from sqlmodel import SQLModel


class Token(SQLModel):
    """Token model for authentication."""

    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    """Token data model."""

    sub: str | None = None
    exp: datetime | None = None


class AuthResponse(SQLModel):
    """Authentication response model."""

    status_code: int
    message: str
    data: Token

    class Config:
        from_attributes = True

