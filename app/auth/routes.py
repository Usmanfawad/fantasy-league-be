from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.auth.service import AuthService
from app.dependencies import AdminUser, CurrentUser
from app.user.models import User, UserCreate, UserLogin, UserRead
from app.utils.db import get_session
from app.utils.responses import ResponseSchema

auth_router = APIRouter(tags=["Auth"])

_login_attempts: dict[str, list[float]] = {}
_LOGIN_WINDOW_SEC = 60
_LOGIN_MAX_ATTEMPTS = 5


@auth_router.post("/sign-up")
async def register(user_create: UserCreate, session: Session = Depends(get_session)):
    try:
        user = await AuthService.create_user(session, user_create)
        return ResponseSchema.success(
            data=UserRead.model_validate(user).model_dump(),
            message="Registration successful",
        )
    except HTTPException as e:
        return ResponseSchema.bad_request(message=str(e.detail))
    except Exception as e:
        return ResponseSchema.bad_request(message=f"Registration failed: {e!s}")


@auth_router.post("/register")
async def register_alias(user_create: UserCreate, session: Session = Depends(get_session)):
    # Alias for spec compatibility
    return await register(user_create, session)


@auth_router.post("/login")
async def login(
    user_login: UserLogin,
    request: Request,
    session: Session = Depends(get_session),
):
    try:
        # Rate limiting per IP
        from time import time

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
        user = await auth_service.authenticate_user(user_login.email, user_login.password)

        if not user:
            return ResponseSchema.unauthorized(
                message="Invalid credentials", error="InvalidCredentials"
            )

        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "role": user.role}
        )

        return ResponseSchema.success(
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "user": UserRead.model_validate(user),
            },
            message="Login successful",
        )

    except Exception as e:
        return ResponseSchema.internal_server_error(message="Login failed", error=str(e))


@auth_router.get("/me", response_model=UserRead)
async def read_users_me(current_user: CurrentUser):
    return current_user


@auth_router.get("/users", response_model=list[UserRead])
async def get_users(admin_user: AdminUser, session: Session = Depends(get_session)):
    try:
        users = session.exec(select(User)).all()
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {e!s}",
        ) from e

