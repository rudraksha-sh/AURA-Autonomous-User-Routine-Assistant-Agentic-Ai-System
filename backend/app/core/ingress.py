from ipaddress import ip_address
from secrets import compare_digest

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings


def register_ingress_guard(app: FastAPI) -> None:
    @app.middleware("http")
    async def ingress_guard(request: Request, call_next):
        secret = settings.aura_proxy_shared_secret.get_secret_value()
        if secret and request.url.path.startswith(("/api/", "/auth/")):
            provided = request.headers.get("x-aura-proxy-token", "")
            if not compare_digest(secret.encode(), provided.encode()):
                return JSONResponse({"message": "API ingress required."}, status_code=403,
                                    headers={"Cache-Control": "no-store"})
            try:
                address = ip_address(request.headers.get("x-aura-client-ip", ""))
            except ValueError:
                return JSONResponse({"message": "Client address unavailable."}, status_code=503,
                                    headers={"Cache-Control": "no-store"})
            request.state.verified_client_ip = str(address)
        return await call_next(request)
