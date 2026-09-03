from fastapi import HTTPException, Request, status

from app.core.rate_limit import RateLimiter


login_limiter = RateLimiter(max_requests=5, window_seconds=60)
register_limiter = RateLimiter(max_requests=5, window_seconds=60)
ai_limiter = RateLimiter(max_requests=10, window_seconds=60)


def get_client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(limiter: RateLimiter, request: Request) -> None:
    if not limiter.allow(get_client_key(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(limiter.window_seconds)},
        )