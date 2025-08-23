from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import Session

from app.db_models import Manager
from app.settings import settings
from app.user.models import UserRole
from app.utils.db import get_session

security = HTTPBearer()


@dataclass
class AuthUser:
    id: UUID
    role: UserRole


class AuthDependency:
    @staticmethod
    async def get_current_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: Session = Depends(get_session),
    ) -> AuthUser:
        """
        Dependency to get the current authenticated user from the JWT token
        """
        try:
            token = credentials.credentials
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )

            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Get manager from database
            manager = session.get(Manager, UUID(user_id))

            if not manager:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Manager not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            auth_user = AuthUser(id=manager.manager_id, role=UserRole.MANAGER)
            request.state.user = auth_user
            return auth_user

        except JWTError as err:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from err
        except Exception as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication error: {err!s}",
            ) from err

    @staticmethod
    def check_roles(allowed_roles: list[UserRole]):
        """
        Dependency factory for role-based access control
        """

        async def role_checker(
            user: AuthUser = Depends(AuthDependency.get_current_user),
        ) -> AuthUser:
            if user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to perform this action",
                )
            return user

        return role_checker


# Common dependencies
get_current_user = AuthDependency.get_current_user
require_admin = AuthDependency.check_roles([UserRole.ADMIN])
require_manager = AuthDependency.check_roles([UserRole.MANAGER, UserRole.ADMIN])
require_user = AuthDependency.check_roles([UserRole.USER, UserRole.MANAGER, UserRole.ADMIN])  # noqa: E501

# Type hints for dependency injection
CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
AdminUser = Annotated[AuthUser, Depends(require_admin)]
ManagerUser = Annotated[AuthUser, Depends(require_manager)]
AnyUser = Annotated[AuthUser, Depends(require_user)]

