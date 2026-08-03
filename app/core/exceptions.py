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


def _sanitize_validation_errors(errors: list[dict]) -> list[dict]:
    """`RequestValidationError.errors()` não aceita `include_context=False` nesta versão do
    FastAPI, e por padrão embute em `ctx.error` o próprio objeto ValueError levantado por um
    `@model_validator` (ex.: SequenceStepIn.valida_tipo) -- não serializável em JSON, derrubava
    a resposta com 500 em vez de 422. Troca o objeto por sua representação em texto.
    """
    sanitized = []
    for e in errors:
        e = dict(e)
        ctx = e.get("ctx")
        if isinstance(ctx, dict) and isinstance(ctx.get("error"), BaseException):
            e["ctx"] = {**ctx, "error": str(ctx["error"])}
        sanitized.append(e)
    return sanitized


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
                                {"errors": _sanitize_validation_errors(exc.errors())}),
        )
