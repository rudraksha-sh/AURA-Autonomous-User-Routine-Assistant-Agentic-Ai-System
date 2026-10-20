from tests.conftest import register_and_verify_email
from datetime import timedelta

from app.core.security import create_access_token

def test_register_user(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test-auth@example.com",
            "password": "TestPassword@123",
            "name": "Test User",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "test-auth@example.com"
    assert data["name"] == "Test User"
    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_registration(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "TestPassword@123",
        "name": "Duplicate User",
    }

    first_response = client.post(
        "/api/auth/register",
        json=payload,
    )

    second_response = client.post(
        "/api/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_login(client):
    response = register_and_verify_email(
        client,
        "login@example.com",
        "TestPassword@123",
        "Login User",
    )

    assert response.status_code == 200, response.text

    data = response.json()
    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"


def test_invalid_login(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "invalid-login@example.com",
            "password": "TestPassword@123",
            "name": "Invalid Login",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "invalid-login@example.com",
            "password": "WrongPassword@123",
        },
    )

    assert response.status_code == 401


def test_me_requires_authentication(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    
def test_malformed_token_is_rejected(client):
    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": "Bearer this-is-not-a-jwt",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"] == "http_error"
    assert response.json()["message"] == "Could not validate credentials"


def test_tampered_token_is_rejected(client):
    token = create_access_token({"sub": "1"})

    tampered_token = token[:-1] + (
        "a" if token[-1] != "a" else "b"
    )

    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {tampered_token}",
        },
    )

    assert response.status_code == 401


def test_expired_token_is_rejected(client):
    token = create_access_token(
        {"sub": "1"},
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401


def test_token_without_subject_is_rejected(client):
    token = create_access_token({})

    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401


def test_token_with_non_numeric_subject_is_rejected(client):
    token = create_access_token({"sub": "not-a-user-id"})

    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401


def test_token_with_non_positive_subject_is_rejected(client):
    for subject in ("0", "-1"):
        token = create_access_token({"sub": subject})

        response = client.get(
            "/api/auth/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )

        assert response.status_code == 401
        
        
def test_login_rate_limit(client):
    from app.core.rate_limit_dependencies import login_limiter

    login_limiter.reset()

    for _ in range(5):
        response = client.post(
            "/api/auth/login",
            json={
                "email": "rate-limit@example.com",
                "password": "wrong-password",
            },
        )

        assert response.status_code == 401

    response = client.post(
        "/api/auth/login",
        json={
            "email": "rate-limit@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"

    login_limiter.reset()
    
def test_register_rate_limit(client):
    from app.core.rate_limit_dependencies import register_limiter

    register_limiter.reset()

    for index in range(5):
        response = client.post(
            "/api/auth/register",
            json={
                "email": f"rate-limit-{index}@example.com",
                "password": "ValidPassword123!",
                "name": "Rate Limit Test",
            },
        )

        assert response.status_code == 201

    response = client.post(
        "/api/auth/register",
        json={
            "email": "rate-limit-final@example.com",
            "password": "ValidPassword123!",
            "name": "Rate Limit Test",
        },
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"

    register_limiter.reset()