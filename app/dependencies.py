from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.settings import settings
from app.user.models import User, UserRole
from app.utils.db import get_session

security = HTTPBearer()


class AuthDependency:
    @staticmethod
    async def get_current_user(
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: Session = Depends(get_session),
    ) -> User:
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

            # Get user from database
            statement = select(User).where(User.id == int(user_id))
            user = session.exec(statement).first()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Inactive user",
                )

            # Add user object to request state
            request.state.user = user
            return user

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication error: {e!s}",
            ) from e

    @staticmethod
    def check_roles(allowed_roles: list[UserRole]):
        """
        Dependency factory for role-based access control
        """

        async def role_checker(
            user: User = Depends(AuthDependency.get_current_user),
        ) -> User:
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
require_user = AuthDependency.check_roles([UserRole.USER, UserRole.MANAGER, UserRole.ADMIN])

# Type hints for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
ManagerUser = Annotated[User, Depends(require_manager)]
AnyUser = Annotated[User, Depends(require_user)]

