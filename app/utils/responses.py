from typing import Any, Generic, TypeVar

from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    status_code: int
    message: str
    data: T | None = None
    error: str | None = None
    meta: dict[str, Any] | None = None


class ResponseSchema:
    @staticmethod
    def success(
        data: Any = None, message: str = "Success", meta: dict[str, Any] | None = None
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=BaseResponse(
                status_code=status.HTTP_200_OK, message=message, data=data, meta=meta
            ).model_dump(exclude_none=True),
        )

    @staticmethod
    def error(
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error: str | None = None,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content=BaseResponse(
                status_code=status_code, message=message, error=error
            ).model_dump(exclude_none=True),
        )

    @staticmethod
    def not_found(
        message: str = "Resource not found", error: str | None = None
    ) -> JSONResponse:
        return ResponseSchema.error(
            message=message, status_code=status.HTTP_404_NOT_FOUND, error=error
        )

    @staticmethod
    def bad_request(
        message: str = "Bad request", error: str | None = None
    ) -> JSONResponse:
        return ResponseSchema.error(
            message=message, status_code=status.HTTP_400_BAD_REQUEST, error=error
        )

    @staticmethod
    def unauthorized(
        message: str = "Unauthorized", error: str | None = None
    ) -> JSONResponse:
        return ResponseSchema.error(
            message=message, status_code=status.HTTP_401_UNAUTHORIZED, error=error
        )

    @staticmethod
    def forbidden(message: str = "Forbidden", error: str | None = None) -> JSONResponse:
        return ResponseSchema.error(
            message=message, status_code=status.HTTP_403_FORBIDDEN, error=error
        )

    @staticmethod
    def internal_server_error(
        message: str = "Internal server error", error: str | None = None
    ) -> JSONResponse:
        return ResponseSchema.error(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=error,
        )

    @staticmethod
    def service_unavailable(
        message: str = "Service temporarily unavailable", error: str | None = None
    ) -> JSONResponse:
        return ResponseSchema.error(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error=error,
        )

    @staticmethod
    def not_implemented(
        message: str = "Not implemented", error: str | None = None
    ) -> JSONResponse:
        return ResponseSchema.error(
            message=message, status_code=status.HTTP_501_NOT_IMPLEMENTED, error=error
        )

    @staticmethod
    def conflict(message: str = "Conflict", error: str | None = None) -> JSONResponse:
        return ResponseSchema.error(
            message=message, status_code=status.HTTP_409_CONFLICT, error=error
        )

    @staticmethod
    def pagination_response(
        data: list[Any], total: int, page: int, page_size: int, message: str = "Success"
    ) -> JSONResponse:
        meta = {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=BaseResponse(
                status_code=status.HTTP_200_OK, message=message, data=data, meta=meta
            ).model_dump(exclude_none=True),
        )

