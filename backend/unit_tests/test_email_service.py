import logging
from unittest.mock import patch

from app.services import email_service


def test_console_email_logs_code_for_local_development(monkeypatch, caplog):
    monkeypatch.setattr(email_service.settings, "email_provider", "console")
    with caplog.at_level(logging.INFO, logger="app.services.email_service"):
        email_service.send_email("person@example.test", "verify_email", "123456")
    assert "person@example.test" in caplog.text
    assert "123456" in caplog.text


def test_email_delivery_failure_is_swallowed_and_does_not_log_exception_text(monkeypatch, caplog):
    def fail(*_args, **_kwargs):
        raise RuntimeError("SMTP password=do-not-log")

    monkeypatch.setattr(email_service, "send_email", fail)
    with caplog.at_level(logging.ERROR, logger="app.services.email_service"):
        email_service.send_email_safely("person@example.test", "reset_password", "123456")
    assert "Failed to send AURA email" in caplog.text
    assert "RuntimeError" in caplog.text
    assert "do-not-log" not in caplog.text
    assert "123456" not in caplog.text


def test_smtp_provider_uses_starttls_and_sends_plain_and_html(monkeypatch):
    captured = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            captured.update(host=host, port=port, timeout=timeout)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def starttls(self):
            captured["starttls"] = True

        def login(self, username, password):
            captured["login"] = (username, password)

        def send_message(self, message):
            captured["message"] = message

    monkeypatch.setattr(email_service.settings, "email_provider", "smtp")
    monkeypatch.setattr(email_service.settings, "smtp_host", "smtp.example.test")
    monkeypatch.setattr(email_service.settings, "smtp_port", 587)
    monkeypatch.setattr(email_service.settings, "smtp_username", "mailer")
    monkeypatch.setattr(email_service.settings, "smtp_password", "test-app-password")
    with patch.object(email_service.smtplib, "SMTP", FakeSMTP):
        email_service.send_email("person@example.test", "verify_email", "654321")
    assert captured["starttls"] is True
    assert captured["login"] == ("mailer", "test-app-password")
    assert "654321" in captured["message"].get_body(preferencelist=("plain",)).get_content()
    assert "654321" in captured["message"].get_body(preferencelist=("html",)).get_content()
