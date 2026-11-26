from fastapi import HTTPException, Request, status

from app.core.rate_limit import RateLimiter
from app.core.config import settings
from app.core.shared_security import PostgresRateLimiter, security_engine


def limiter(policy: str, max_requests: int, window_seconds: int) -> RateLimiter | PostgresRateLimiter:
    if security_engine is None:
        return RateLimiter(max_requests, window_seconds)
    return PostgresRateLimiter(
        security_engine, policy, max_requests, window_seconds, digest_key=settings.jwt_secret_key,
    )


oauth_connect_limiter = limiter("oauth_connect", 10, 60)
google_read_limiter = limiter("google_read", 20, 60)
login_limiter = limiter("login", 5, 60)
register_limiter = limiter("register", 5, 60)
workflow_limiter = limiter("workflow", 20, 60)
ai_limiter = limiter("ai", 10, 60)
verify_email_limiter = limiter("verify_email", 5, 300)
resend_verification_limiter = limiter("resend_verification", 3, 300)
forgot_password_limiter = limiter("forgot_password", 3, 300)
reset_password_limiter = limiter("reset_password", 5, 300)
two_factor_limiter = limiter("two_factor", 10, 300)


def get_client_key(request: Request) -> str:
    if verified := getattr(request.state, "verified_client_ip", None):
        return verified
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(limiter: RateLimiter | PostgresRateLimiter, request: Request) -> None:
    if not limiter.allow(get_client_key(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(limiter.window_seconds)},
        )


def enforce_auth_rate_limit(limiter: RateLimiter | PostgresRateLimiter, request: Request, email: str) -> None:
    ip_key = f"ip:{get_client_key(request)}"
    email_key = f"email:{email.strip().lower()}"
    if not limiter.allow(ip_key) or not limiter.allow(email_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(limiter.window_seconds)},
        )
