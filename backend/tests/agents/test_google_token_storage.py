import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from app.core.config import settings
from app.integrations.google.token_storage import TokenStorageError, protect_token, reveal_token


def test_tokens_remain_readable_during_rollout_and_fail_closed_with_wrong_key(monkeypatch):
    monkeypatch.setattr(settings, "integration_token_key", SecretStr(Fernet.generate_key().decode()))
    assert reveal_token("existing-plaintext-token") == "existing-plaintext-token"
    protected = protect_token("new-test-token")
    assert protected != "new-test-token"
    assert reveal_token(protected) == "new-test-token"
    assert protect_token(protected) == protected
    monkeypatch.setattr(settings, "integration_token_key", SecretStr(Fernet.generate_key().decode()))
    with pytest.raises(TokenStorageError, match="could not be decrypted"):
        reveal_token(protected)
