from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppException(Exception):
    """Base application exception for all domain and HTTP errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class UnauthenticatedException(AppException):
    """Raised when authentication credentials are missing, invalid, or expired."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            message=message,
            code="UNAUTHENTICATED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenException(AppException):
    """Raised when an authenticated user lacks permission for an operation."""

    def __init__(self, message: str = "Access forbidden") -> None:
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class InvalidRequestException(AppException):
    """Raised when request payload or headers are invalid."""

    def __init__(self, message: str = "Invalid request") -> None:
        super().__init__(
            message=message,
            code="INVALID_REQUEST",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class NotFoundException(AppException):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class PayloadTooLargeException(AppException):
    """Raised when an uploaded file exceeds the configured maximum size limit."""

    def __init__(self, message: str = "File too large") -> None:
        super().__init__(
            message=message,
            code="FILE_TOO_LARGE",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


class UnsupportedMediaTypeException(AppException):
    """Raised when an uploaded file type or content signature is unsupported."""

    def __init__(self, message: str = "Unsupported file type") -> None:
        super().__init__(
            message=message,
            code="UNSUPPORTED_FILE_TYPE",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )


def _format_error_response(
    code: str,
    message: str,
    status_code: int,
    request_id: str | None = None,
    details: Any = None,
) -> JSONResponse:
    """Builds a standardized error envelope matching the API contract."""
    content: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }
    if details is not None:
        content["error"]["details"] = details

    return JSONResponse(
        status_code=status_code,
        content=content,
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Registers standard exception handlers on the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        return _format_error_response(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        code_map = {
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "RESOURCE_NOT_FOUND",
            400: "INVALID_REQUEST",
            413: "FILE_TOO_LARGE",
            415: "UNSUPPORTED_FILE_TYPE",
        }
        code = code_map.get(exc.status_code, "INTERNAL_ERROR")
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _format_error_response(
            code=code,
            message=detail,
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        field_errors: list[str] = []
        details: list[dict[str, str]] = []
        for err in exc.errors():
            loc_parts = [str(x) for x in err.get("loc", []) if x != "body"]
            field_name = ".".join(loc_parts) if loc_parts else "body"
            msg = err.get("msg", "Invalid value")
            field_errors.append(f"'{field_name}': {msg}")
            details.append({"field": field_name, "message": msg})

        detail_summary = (
            "; ".join(field_errors) if field_errors else "Invalid request data"
        )
        return _format_error_response(
            code="VALIDATION_ERROR",
            message=f"Validation error: {detail_summary}",
            status_code=422,
            details=details if details else None,
        )

