import asyncio
import time
from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import rate_limit_dependencies as limits
from app.core.config import settings
from app.core.rate_limit_dependencies import enforce_auth_rate_limit, enforce_rate_limit
from app.core.security import create_access_token, decode_access_token, get_current_user, get_current_user_id, hash_password, verify_password
from app.db.session import get_db
from app.models.otp_code import OtpPurpose
from app.models.user import User
from app.schemas.auth import (
    EmailCodeRequest,
    EmailRequest,
    LoginOtpRequest,
    LoginRequest,
    LoginResponse,
    PasswordResetRequest,
    TokenResponse,
    TwoFactorCodeRequest,
    TwoFactorRequest,
    UserCreate,
    UserResponse,
)
from app.services.email_service import send_email_safely
from app.services.otp_service import OtpCooldownError, issue_otp, verify_otp


router = APIRouter(prefix="/auth", tags=["Authentication"])
GENERIC_RECOVERY_MESSAGE = "If an account exists for that email, we sent a code."
GENERIC_RESEND_MESSAGE = "If the account needs verification, a code has been sent."


def _token_response(user: User) -> dict:
    return {
        "access_token": create_access_token({"sub": str(user.id), "ver": user.token_version}),
        "token_type": "bearer",
        "requires_otp": False,
        "challenge_id": None,
    }


def _issue_and_send(db: Session, background_tasks: BackgroundTasks, user: User, purpose: OtpPurpose, kind: str) -> None:
    code = issue_otp(db, user.id, purpose)
    background_tasks.add_task(send_email_safely, user.email, kind, code)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    enforce_rate_limit(limits.register_limiter, request)
    email = str(user_data.email).lower()
    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")
    user = User(email=email, password_hash=hash_password(user_data.password), name=user_data.name, email_verified=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    _issue_and_send(db, background_tasks, user, OtpPurpose.VERIFY_EMAIL, "verify_email")
    return user


@router.post("/verify-email")
def verify_email(data: EmailCodeRequest, request: Request, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    enforce_auth_rate_limit(limits.verify_email_limiter, request, email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None or user.email_verified or not verify_otp(db, user.id, OtpPurpose.VERIFY_EMAIL, data.code):
        raise HTTPException(status_code=400, detail="The verification code is invalid or expired")
    user.email_verified = True
    db.commit()
    return {"message": "Email verified. You can now sign in."}


@router.post("/resend-verification")
def resend_verification(data: EmailRequest, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    enforce_auth_rate_limit(limits.resend_verification_limiter, request, email)
    user = db.scalar(select(User).where(User.email == email))
    if user and not user.email_verified:
        try:
            _issue_and_send(db, background_tasks, user, OtpPurpose.VERIFY_EMAIL, "verify_email")
        except OtpCooldownError:
            pass
    return {"message": GENERIC_RESEND_MESSAGE}


@router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    enforce_rate_limit(limits.login_limiter, request)
    email = str(login_data.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.email_verified:
        try:
            _issue_and_send(db, background_tasks, user, OtpPurpose.VERIFY_EMAIL, "verify_email")
        except OtpCooldownError:
            pass
        return JSONResponse(status_code=403, content={"error": "email_not_verified", "message": "Verify your email before signing in."})
    if user.two_factor_enabled:
        try:
            code = issue_otp(db, user.id, OtpPurpose.LOGIN_2FA)
        except OtpCooldownError as error:
            raise HTTPException(status_code=429, detail=str(error), headers={"Retry-After": str(error.retry_after)})
        challenge_id = create_access_token(
            {"sub": str(user.id), "ver": user.token_version, "purpose": "login_2fa", "jti": secrets.token_urlsafe(24)},
            expires_delta=timedelta(minutes=settings.otp_expiry_minutes),
        )
        background_tasks.add_task(send_email_safely, user.email, "login_2fa", code)
        return {"requires_otp": True, "challenge_id": challenge_id}
    return _token_response(user)


@router.post("/login/verify-otp", response_model=TokenResponse)
def verify_login_otp(data: LoginOtpRequest, request: Request, db: Session = Depends(get_db)):
    enforce_rate_limit(limits.two_factor_limiter, request)
    try:
        claims = decode_access_token(data.challenge_id)
        if claims.get("purpose") != "login_2fa" or not claims.get("jti"):
            raise ValueError
        user_id = int(claims.get("sub", ""))
        version = claims.get("ver", 0)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=400, detail="The sign-in code is invalid or expired")
    user = db.get(User, user_id)
    if user is None or not user.two_factor_enabled or not user.email_verified or version != user.token_version:
        raise HTTPException(status_code=400, detail="The sign-in code is invalid or expired")
    if not verify_otp(db, user.id, OtpPurpose.LOGIN_2FA, data.code):
        raise HTTPException(status_code=400, detail="The sign-in code is invalid or expired")
    return _token_response(user)


@router.post("/forgot-password")
async def forgot_password(data: EmailRequest, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    started = time.perf_counter()
    email = str(data.email).lower()
    enforce_auth_rate_limit(limits.forgot_password_limiter, request, email)
    user = db.scalar(select(User).where(User.email == email))
    if user:
        try:
            _issue_and_send(db, background_tasks, user, OtpPurpose.RESET_PASSWORD, "reset_password")
        except OtpCooldownError:
            pass
    # Keep response timing close for known and unknown addresses.
    await asyncio.sleep(max(0.0, 0.1 - (time.perf_counter() - started)))
    return {"message": GENERIC_RECOVERY_MESSAGE}


@router.post("/reset-password")
def reset_password(data: PasswordResetRequest, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    enforce_auth_rate_limit(limits.reset_password_limiter, request, email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_otp(db, user.id, OtpPurpose.RESET_PASSWORD, data.code):
        raise HTTPException(status_code=400, detail="The reset code is invalid or expired")
    if verify_password(data.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Choose a password different from your current one")
    user.password_hash = hash_password(data.new_password)
    user.token_version += 1
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    background_tasks.add_task(send_email_safely, user.email, "password_changed", None)
    return {"message": "Password reset successfully. Please sign in with your new password."}


@router.post("/2fa/send-code")
def send_two_factor_code(
    data: TwoFactorCodeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(limits.two_factor_limiter, request)
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if (data.action == "enable") == user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="Two-step login is already in that state")
    purpose = OtpPurpose.ENABLE_2FA if data.action == "enable" else OtpPurpose.DISABLE_2FA
    email_kind = "enable_2fa" if data.action == "enable" else "disable_2fa"
    try:
        _issue_and_send(db, background_tasks, user, purpose, email_kind)
    except OtpCooldownError as error:
        raise HTTPException(status_code=429, detail=str(error), headers={"Retry-After": str(error.retry_after)})
    return {"message": "A confirmation code was sent to your email."}


@router.get("/security")
def get_security_settings(user: User = Depends(get_current_user)):
    return {"email_verified": user.email_verified, "two_factor_enabled": user.two_factor_enabled}


@router.post("/2fa/enable")
def enable_two_factor(data: TwoFactorRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(limits.two_factor_limiter, request)
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if user.two_factor_enabled or not verify_otp(db, user.id, OtpPurpose.ENABLE_2FA, data.code):
        raise HTTPException(status_code=400, detail="The confirmation code is invalid or expired")
    user.two_factor_enabled = True
    db.commit()
    return {"two_factor_enabled": True}


@router.post("/2fa/disable")
def disable_two_factor(data: TwoFactorRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(limits.two_factor_limiter, request)
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if not user.two_factor_enabled or not verify_otp(db, user.id, OtpPurpose.DISABLE_2FA, data.code):
        raise HTTPException(status_code=400, detail="The confirmation code is invalid or expired")
    user.two_factor_enabled = False
    db.commit()
    return {"two_factor_enabled": False}


@router.get("/me", response_model=UserResponse)
def get_me(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    user.token_version += 1
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
