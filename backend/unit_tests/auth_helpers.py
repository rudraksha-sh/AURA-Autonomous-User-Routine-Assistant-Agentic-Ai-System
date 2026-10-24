from app.api.routes import auth as auth_routes

_CAPTURED_EMAIL_CODES: dict[tuple[str, str], str] = {}


def verify_registered_email(client, email: str) -> None:
    code = _CAPTURED_EMAIL_CODES[(email.lower(), "verify_email")]
    response = client.post(
        "/api/auth/verify-email",
        json={"email": email, "code": code},
    )
    assert response.status_code == 200, response.text


def register_verified(client, payload: dict):
    _CAPTURED_EMAIL_CODES.clear()
    original_sender = auth_routes.send_email_safely

    def capture_email_code(email: str, kind: str, code: str | None = None) -> None:
        if code:
            _CAPTURED_EMAIL_CODES[(email.lower(), kind)] = code

    auth_routes.send_email_safely = capture_email_code
    try:
        response = client.post("/api/auth/register", json=payload)
    finally:
        auth_routes.send_email_safely = original_sender

    assert response.status_code == 201, response.text
    verify_registered_email(client, payload["email"])
    return response
