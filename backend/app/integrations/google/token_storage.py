from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

PREFIX = "fernet:v1:"


class TokenStorageError(ValueError):
    """A stored integration token could not be safely read."""


def protect_token(value: str | None) -> str | None:
    if value is None or value.startswith(PREFIX):
        return value
    key = settings.integration_token_key.get_secret_value()
    if not key:
        return value
    return PREFIX + Fernet(key.encode()).encrypt(value.encode()).decode("ascii")


def reveal_token(value: str | None) -> str | None:
    if value is None or not value.startswith(PREFIX):
        return value
    try:
        key = settings.integration_token_key.get_secret_value().encode()
        return Fernet(key).decrypt(value[len(PREFIX):].encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise TokenStorageError("The integration token could not be decrypted.") from exc
