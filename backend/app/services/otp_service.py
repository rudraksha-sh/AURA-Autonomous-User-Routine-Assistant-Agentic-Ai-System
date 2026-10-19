import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.otp_code import OtpCode, OtpPurpose


class OtpCooldownError(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__("Please wait before requesting another code.")


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(code: str) -> str:
    key = (settings.otp_pepper or settings.jwt_secret_key).encode("utf-8")
    return hmac.new(key, code.encode("ascii"), hashlib.sha256).hexdigest()


def issue_otp(
    db: Session,
    user_id: int,
    purpose: OtpPurpose,
    *,
    now: datetime | None = None,
) -> str:
    now = now or datetime.now(timezone.utc)
    purpose_value = purpose.value
    latest = db.scalar(
        select(OtpCode)
        .where(OtpCode.user_id == user_id, OtpCode.purpose == purpose_value)
        .order_by(OtpCode.created_at.desc(), OtpCode.id.desc())
        .limit(1)
    )
    if latest:
        elapsed = (_utc(now) - _utc(latest.created_at)).total_seconds()
        if elapsed < settings.otp_resend_cooldown_seconds:
            raise OtpCooldownError(max(1, int(settings.otp_resend_cooldown_seconds - elapsed)))
    db.execute(
        OtpCode.__table__.update()
        .where(OtpCode.user_id == user_id, OtpCode.purpose == purpose_value, OtpCode.consumed_at.is_(None))
        .values(consumed_at=now)
    )
    code = generate_code()
    db.add(OtpCode(
        user_id=user_id,
        purpose=purpose_value,
        code_hash=hash_code(code),
        expires_at=now + timedelta(minutes=settings.otp_expiry_minutes),
        created_at=now,
    ))
    db.commit()
    return code


def verify_otp(
    db: Session,
    user_id: int,
    purpose: OtpPurpose,
    code: str,
    *,
    now: datetime | None = None,
) -> bool:
    now = now or datetime.now(timezone.utc)
    otp = db.scalar(
        select(OtpCode)
        .where(
            OtpCode.user_id == user_id,
            OtpCode.purpose == purpose.value,
            OtpCode.consumed_at.is_(None),
        )
        .order_by(OtpCode.created_at.desc(), OtpCode.id.desc())
        .with_for_update()
        .limit(1)
    )
    if otp is None:
        return False
    if _utc(otp.expires_at) <= _utc(now) or otp.attempts >= settings.otp_max_attempts:
        otp.consumed_at = now
        db.commit()
        return False
    if not hmac.compare_digest(otp.code_hash, hash_code(code)):
        otp.attempts += 1
        if otp.attempts >= settings.otp_max_attempts:
            otp.consumed_at = now
        db.commit()
        return False
    otp.consumed_at = now
    db.commit()
    return True
