from conftest import CAPTURED_EMAIL_CODES


def verify_registered_email(client, email: str) -> None:
    code = CAPTURED_EMAIL_CODES[(email.lower(), "verify_email")]
    response = client.post("/api/auth/verify-email", json={"email": email, "code": code})
    assert response.status_code == 200, response.text


def register_verified(client, payload: dict):
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    verify_registered_email(client, payload["email"])
    return response
