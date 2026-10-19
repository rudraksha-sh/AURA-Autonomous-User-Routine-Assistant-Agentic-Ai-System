from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.otp_code import OtpCode, OtpPurpose
from app.models.user import User
from app.services import otp_service


def _db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'otp.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(User(email="otp@example.com", name="OTP", password_hash="unused"))
    session.commit()
    user = session.scalar(select(User).where(User.email == "otp@example.com"))
    return engine, session, user.id


def test_codes_are_six_digit_hmac_values_and_single_use(tmp_path, monkeypatch):
    engine, db, user_id = _db(tmp_path)
    monkeypatch.setattr(otp_service, "generate_code", lambda: "004271")
    code = otp_service.issue_otp(db, user_id, OtpPurpose.VERIFY_EMAIL)
    otp = db.scalar(select(OtpCode))
    assert code == "004271"
    assert otp.code_hash == otp_service.hash_code(code)
    assert otp.code_hash != code
    assert otp_service.verify_otp(db, user_id, OtpPurpose.VERIFY_EMAIL, code)
    assert not otp_service.verify_otp(db, user_id, OtpPurpose.VERIFY_EMAIL, code)
    db.close()
    engine.dispose()


def test_wrong_attempts_expire_and_purposes_are_isolated(tmp_path, monkeypatch):
    engine, db, user_id = _db(tmp_path)
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(otp_service.settings, "otp_max_attempts", 2)
    monkeypatch.setattr(otp_service, "generate_code", lambda: "123456")
    otp_service.issue_otp(db, user_id, OtpPurpose.RESET_PASSWORD, now=now)
    assert not otp_service.verify_otp(db, user_id, OtpPurpose.VERIFY_EMAIL, "123456", now=now)
    assert not otp_service.verify_otp(db, user_id, OtpPurpose.RESET_PASSWORD, "000000", now=now)
    assert not otp_service.verify_otp(db, user_id, OtpPurpose.RESET_PASSWORD, "000001", now=now)
    assert not otp_service.verify_otp(db, user_id, OtpPurpose.RESET_PASSWORD, "123456", now=now)

    monkeypatch.setattr(otp_service.settings, "otp_max_attempts", 5)
    monkeypatch.setattr(otp_service.settings, "otp_expiry_minutes", 1)
    otp_service.issue_otp(db, user_id, OtpPurpose.VERIFY_EMAIL, now=now + timedelta(minutes=2))
    assert not otp_service.verify_otp(db, user_id, OtpPurpose.VERIFY_EMAIL, "123456", now=now + timedelta(minutes=4))
    db.close()
    engine.dispose()


def test_new_code_invalidates_old_and_cooldown_is_enforced(tmp_path, monkeypatch):
    engine, db, user_id = _db(tmp_path)
    monkeypatch.setattr(otp_service.settings, "otp_resend_cooldown_seconds", 30)
    monkeypatch.setattr(otp_service, "generate_code", iter(["111111", "222222"]).__next__)
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    first = otp_service.issue_otp(db, user_id, OtpPurpose.VERIFY_EMAIL, now=now)
    try:
        otp_service.issue_otp(db, user_id, OtpPurpose.VERIFY_EMAIL, now=now + timedelta(seconds=10))
        assert False, "cooldown should reject a resend"
    except otp_service.OtpCooldownError as error:
        assert error.retry_after == 20
    second = otp_service.issue_otp(db, user_id, OtpPurpose.VERIFY_EMAIL, now=now + timedelta(seconds=30))
    assert second != first
    assert not otp_service.verify_otp(db, user_id, OtpPurpose.VERIFY_EMAIL, first, now=now + timedelta(seconds=31))
    assert otp_service.verify_otp(db, user_id, OtpPurpose.VERIFY_EMAIL, second, now=now + timedelta(seconds=31))
    db.close()
    engine.dispose()
