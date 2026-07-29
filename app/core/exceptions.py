"""Exceções de domínio e handlers para envelope de erro consistente."""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Exceção base da aplicação."""
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "bad_request"

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def _app_exc(request: Request, exc: AppException):
        return JSONResponse(status_code=exc.status_code,
                            content=_error_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body("validation_error", "Dados inválidos",
                                {"errors": exc.errors()}),
        )
