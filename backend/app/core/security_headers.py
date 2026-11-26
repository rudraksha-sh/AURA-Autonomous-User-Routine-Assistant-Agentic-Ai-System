from fastapi import FastAPI, Request
from fastapi.responses import Response


def register_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers_middleware(
        request: Request,
        call_next,
    ) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        path = request.url.path
        response.headers["Referrer-Policy"] = (
            "no-referrer" if path.rstrip("/") == "/api/integrations/google/callback"
            else "strict-origin-when-cross-origin"
        )
        if path.startswith(("/api/", "/auth/")):
            directives = {item.strip().lower() for item in response.headers.get("Cache-Control", "").split(",")}
            if "no-store" not in directives:
                response.headers["Cache-Control"] = "no-store"

        return response