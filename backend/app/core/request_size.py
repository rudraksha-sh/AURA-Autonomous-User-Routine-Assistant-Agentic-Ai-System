"""Bound request bytes before application parsing, including streamed bodies."""
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

MAX_REQUEST_BYTES = 6 * 1024 * 1024
DETAIL = "Request body is too large."


class RequestSizeLimit:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_REQUEST_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for name, value in scope["headers"]:
            if name == b"content-length" and value.isdigit() and (
                len(value.lstrip(b"0")) > len(str(self.max_bytes))
                or int(value.lstrip(b"0") or b"0") > self.max_bytes
            ):
                await JSONResponse({"error": "http_error", "message": DETAIL}, 413)(scope, receive, send)
                return

        size = 0

        async def limited_receive():
            nonlocal size
            message = await receive()
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > self.max_bytes:
                    raise HTTPException(413, DETAIL)
            return message

        await self.app(scope, limited_receive, send)
