import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


from app.core.shared_security import SecurityStateUnavailable


logger = logging.getLogger("aura.api")


def register_exception_handlers(app: FastAPI) -> None:
    """Register safe, centralized API exception handlers."""

    @app.exception_handler(SecurityStateUnavailable)
    async def shared_state_unavailable(_: Request, __: SecurityStateUnavailable) -> JSONResponse:
        logger.warning("shared_security_state_unavailable")
        return JSONResponse(
            status_code=503, headers={"Retry-After": "2"},
            content={"error": "security_state_unavailable", "message": "Try again shortly."},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.warning(
            "Request validation failed: method=%s route=%s count=%s",
            request.method,
            getattr(request.scope.get("route"), "path", "<unmatched>"),
            len(exc.errors()),
        )

        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": str(exc.detail),
            },
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.error(
            "Unhandled application exception: method=%s route=%s type=%s",
            request.method,
            getattr(request.scope.get("route"), "path", "<unmatched>"),
            type(exc).__name__,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred",
            },
        )
