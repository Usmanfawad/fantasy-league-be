from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.dependencies import require_admin, require_manager, require_user
from app.user.models import UserCreate, UserRead, UserUpdate
from app.user.service import UserService
from app.utils.db import get_session

user_router = APIRouter(tags=["Managers"])


@user_router.get("/me", response_model=UserRead)
async def read_managers_me(current_user=Depends(require_user)):
    """Get current manager information."""
    return current_user


@user_router.get("/{manager_id}", response_model=UserRead)
async def read_manager(
    manager_id: int,
    current_user=Depends(require_manager),
    session: Session = Depends(get_session),
):
    """Get manager by ID."""
    user_service = UserService(session)
    user = user_service.get_user_by_id(manager_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")
    return user


@user_router.get("/", response_model=list[UserRead])
async def read_managers(
    skip: int = 0,
    limit: int = 100,
    current_user=Depends(require_manager),
    session: Session = Depends(get_session),
):
    """Get list of managers."""
    user_service = UserService(session)
    return user_service.get_users(skip=skip, limit=limit)


@user_router.post("/", response_model=UserRead)
async def create_manager(
    user_data: UserCreate,
    current_user=Depends(require_admin),
    session: Session = Depends(get_session),
):
    """Create new manager."""
    user_service = UserService(session)
    if user_service.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    return user_service.create_user(user_data)


@user_router.put("/{manager_id}", response_model=UserRead)
async def update_manager(
    manager_id: int,
    user_data: UserUpdate,
    current_user=Depends(require_admin),
    session: Session = Depends(get_session),
):
    """Update manager."""
    user_service = UserService(session)
    user = user_service.update_user(manager_id, user_data)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")
    return user


@user_router.delete("/{manager_id}")
async def delete_manager(
    manager_id: int,
    current_user=Depends(require_admin),
    session: Session = Depends(get_session),
):
    """Delete manager."""
    user_service = UserService(session)
    if not user_service.delete_user(manager_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")
    return {"message": "Manager deleted successfully"}

