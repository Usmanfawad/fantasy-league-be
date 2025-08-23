from datetime import datetime
from time import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlmodel import Session, select

from app.auth.service import AuthService
from app.db_models import Manager
from app.dependencies import CurrentUser
from app.utils.db import get_session
from app.utils.responses import ResponseSchema

auth_router = APIRouter(tags=["Auth"])

_login_attempts: dict[str, list[float]] = {}
_LOGIN_WINDOW_SEC = 60
_LOGIN_MAX_ATTEMPTS = 5


class ManagerSignUp(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    password: str
    birthdate: str | None = Field(
        default=None,
        description="Date of birth in DD-MM-YYYY format",
        examples=["25-12-1990"],
        json_schema_extra={"format": "DD-MM-YYYY"}
    )
    city: str | None = None
    fav_team: int | None = None
    fav_player: str | None = None
    squad_name: str

    @field_validator('birthdate')
    @classmethod
    def validate_birthdate(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            # Try to parse the date in DD-MM-YYYY format
            datetime.strptime(v, "%d-%m-%Y")
            return v
        except ValueError as e:
            raise ValueError("birthdate must be in DD-MM-YYYY format") from e


class ManagerLogin(BaseModel):
    email: EmailStr
    password: str


@auth_router.post("/sign-up")
async def register(manager: ManagerSignUp, session: Session = Depends(get_session)):
    try:
        created = await AuthService.create_manager(session, manager.model_dump())
        return ResponseSchema.success(
            data={"manager_id": str(created.manager_id)},
            message="Account created successfully",
        )
    except HTTPException as e:
        return ResponseSchema.bad_request(message=str(e.detail))
    except Exception as e:
        return ResponseSchema.bad_request(message=f"Registration failed: {e!s}")



@auth_router.post("/login")
async def login(
    user_login: ManagerLogin,
    request: Request,
    session: Session = Depends(get_session),
):
    try:
        # Rate limiting per IP

        ip = request.client.host if request.client else "unknown"
        now = time()
        window = _login_attempts.get(ip, [])
        window = [t for t in window if now - t < _LOGIN_WINDOW_SEC]
        if len(window) >= _LOGIN_MAX_ATTEMPTS:
            return ResponseSchema.forbidden(
                message="Too many login attempts. Please try again later.",
                error="RateLimited",
            )
        window.append(now)
        _login_attempts[ip] = window

        auth_service = AuthService(session)
        manager: Manager = await auth_service.authenticate_manager(
            user_login.email, user_login.password
        )

        if not manager:
            return ResponseSchema.unauthorized(
                message="Invalid credentials", error="InvalidCredentials"
            )

        access_token = auth_service.create_access_token(
            data={
                "sub": str(manager.manager_id),
                "role": "manager",
                "email": manager.email,
                "squad_name": manager.squad_name,
            }
        )

        return ResponseSchema.success(
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "manager_id": str(manager.manager_id),
                "squad_name": manager.squad_name,
            },
            message="Login successful",
        )

    except Exception as e:
        return ResponseSchema.internal_server_error(
            message="Login failed", error=str(e)
        )


@auth_router.get("/me")
async def read_managers_me(current_user: CurrentUser, session: Session = Depends(get_session)):
    # current_user is a lightweight auth user; fetch full manager info
    mgr = session.get(Manager, current_user.id)
    if not mgr:
        return ResponseSchema.not_found("Manager not found")
    return ResponseSchema.success(
        data={
            "manager_id": str(mgr.manager_id),
            "email": mgr.email,
            "squad_name": mgr.squad_name,
            "firstname": mgr.mng_firstname,
            "lastname": mgr.mng_lastname,
        }
    )


# Optional utility endpoint to list managers (simple pagination could be added)
@auth_router.get("/managers")
async def get_managers(session: Session = Depends(get_session)):
    rows = session.exec(select(Manager)).all()
    return ResponseSchema.success(
        data=[{"manager_id": str(m.manager_id), "email": m.email, "squad_name": m.squad_name} for m in rows]
    )

