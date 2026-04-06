"""
Centralised error handler — converts unhandled exceptions into
consistent JSON error envelopes so clients always get the same shape.
"""
import structlog
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = structlog.get_logger()


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception("unhandled_error", path=request.url.path, error=str(exc))
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Internal server error", "data": None},
            )
