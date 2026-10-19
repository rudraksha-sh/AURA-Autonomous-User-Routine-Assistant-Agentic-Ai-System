from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.session import Base, get_db
from app.main import app
from app.models.otp_code import OtpCode
from app.models.user import User
from conftest import CAPTURED_EMAIL_CODES
from auth_helpers import register_verified


def _client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth-otp.db'}")
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    return engine, TestClient(app), previous


def _headers(client, email, password="StrongPass123!"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_register_verify_then_login_and_unverified_login_blocked(tmp_path):
    engine, client, previous = _client(tmp_path)
    email = "verify-flow@example.com"
    try:
        response = client.post("/api/auth/register", json={"name": "Verify", "email": email, "password": "StrongPass123!"})
        assert response.status_code == 201
        assert response.json()["email_verified"] is False
        blocked = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
        assert blocked.status_code == 403
        assert blocked.json()["error"] == "email_not_verified"
        code = CAPTURED_EMAIL_CODES[(email, "verify_email")]
        assert client.post("/api/auth/verify-email", json={"email": email, "code": code}).status_code == 200
        assert client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"}).status_code == 200
        with Session(engine) as db:
            user = db.scalar(select(User).where(User.email == email))
            assert user.email_verified is True
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def test_forgot_password_is_generic_and_reset_invalidates_old_tokens(tmp_path):
    engine, client, previous = _client(tmp_path)
    email = "reset-flow@example.com"
    try:
        register_verified(client, {"name": "Reset", "email": email, "password": "StrongPass123!"})
        old_headers = _headers(client, email)
        existing = client.post("/api/auth/forgot-password", json={"email": email})
        unknown = client.post("/api/auth/forgot-password", json={"email": "unknown@example.com"})
        assert existing.status_code == unknown.status_code == 200
        assert existing.json() == unknown.json()
        code = CAPTURED_EMAIL_CODES[(email, "reset_password")]
        result = client.post("/api/auth/reset-password", json={
            "email": email, "code": code, "new_password": "ChangedPass456!",
        })
        assert result.status_code == 200
        assert client.get("/api/auth/me", headers=old_headers).status_code == 401
        assert client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"}).status_code == 401
        assert client.post("/api/auth/login", json={"email": email, "password": "ChangedPass456!"}).status_code == 200
        with Session(engine) as db:
            assert db.scalar(select(OtpCode).where(OtpCode.user_id == 1, OtpCode.purpose == "reset_password")).consumed_at is not None
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def test_forgot_password_is_rate_limited_by_client_ip(tmp_path):
    engine, client, previous = _client(tmp_path)
    try:
        for index in range(3):
            response = client.post("/api/auth/forgot-password", json={"email": f"unknown-{index}@example.com"})
            assert response.status_code == 200
        limited = client.post("/api/auth/forgot-password", json={"email": "another-unknown@example.com"})
        assert limited.status_code == 429
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def test_two_factor_enable_challenge_wrong_code_and_single_use(tmp_path):
    engine, client, previous = _client(tmp_path)
    email = "two-factor@example.com"
    try:
        register_verified(client, {"name": "Two Factor", "email": email, "password": "StrongPass123!"})
        headers = _headers(client, email)
        send = client.post("/api/auth/2fa/send-code", headers=headers, json={"current_password": "StrongPass123!", "action": "enable"})
        assert send.status_code == 200
        code = CAPTURED_EMAIL_CODES[(email, "enable_2fa")]
        wrong_code = "000000" if code != "000000" else "000001"
        assert client.post("/api/auth/2fa/enable", headers=headers, json={"current_password": "StrongPass123!", "code": wrong_code}).status_code == 400
        assert client.post("/api/auth/2fa/enable", headers=headers, json={"current_password": "StrongPass123!", "code": code}).json() == {"two_factor_enabled": True}
        challenge = client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"})
        assert challenge.status_code == 200 and challenge.json()["requires_otp"] is True
        challenge_headers = {"Authorization": f"Bearer {challenge.json()['challenge_id']}"}
        assert client.get("/api/auth/me", headers=challenge_headers).status_code == 401
        login_code = CAPTURED_EMAIL_CODES[(email, "login_2fa")]
        wrong_login_code = "000000" if login_code != "000000" else "000001"
        assert client.post("/api/auth/login/verify-otp", json={"challenge_id": challenge.json()["challenge_id"], "code": wrong_login_code}).status_code == 400
        verified = client.post("/api/auth/login/verify-otp", json={"challenge_id": challenge.json()["challenge_id"], "code": login_code})
        assert verified.status_code == 200 and verified.json()["access_token"]
        assert client.post("/api/auth/login/verify-otp", json={"challenge_id": challenge.json()["challenge_id"], "code": login_code}).status_code == 400
        signed_in = {"Authorization": f"Bearer {verified.json()['access_token']}"}
        disable_request = client.post("/api/auth/2fa/send-code", headers=signed_in, json={"current_password": "StrongPass123!", "action": "disable"})
        assert disable_request.status_code == 200
        disable_code = CAPTURED_EMAIL_CODES[(email, "disable_2fa")]
        disabled = client.post("/api/auth/2fa/disable", headers=signed_in, json={"current_password": "StrongPass123!", "code": disable_code})
        assert disabled.status_code == 200 and disabled.json()["two_factor_enabled"] is False
        assert client.post("/api/auth/login", json={"email": email, "password": "StrongPass123!"}).json()["access_token"]
    finally:
        client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()
