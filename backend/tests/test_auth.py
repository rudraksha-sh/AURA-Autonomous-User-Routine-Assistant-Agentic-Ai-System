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
    client.post(
        "/api/auth/register",
        json={
            "email": "login@example.com",
            "password": "TestPassword@123",
            "name": "Login User",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={
            "email": "login@example.com",
            "password": "TestPassword@123",
        },
    )

    assert response.status_code == 200

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