import logging
import smtplib
from email.message import EmailMessage
from html import escape
from typing import Literal, Protocol

from app.core.config import settings


logger = logging.getLogger(__name__)
EmailKind = Literal["verify_email", "reset_password", "password_changed", "login_2fa", "enable_2fa", "disable_2fa"]


SUBJECTS: dict[EmailKind, str] = {
    "verify_email": "Verify your AURA email",
    "reset_password": "Reset your AURA password",
    "password_changed": "Your AURA password was changed",
    "login_2fa": "Your AURA sign-in code",
    "enable_2fa": "Confirm two-step login for AURA",
    "disable_2fa": "Confirm disabling two-step login for AURA",
}


def _content(kind: EmailKind, code: str | None) -> tuple[str, str]:
    if kind == "password_changed":
        plain = "Your AURA password was changed. If you did not make this change, contact support immediately."
        return plain, f"<p>{escape(plain)}</p>"
    action = {
        "verify_email": "verify your email address",
        "reset_password": "reset your password",
        "login_2fa": "sign in to AURA",
        "enable_2fa": "enable two-step login",
        "disable_2fa": "disable two-step login",
    }[kind]
    plain = f"Use this code to {action}: {code}\n\nThe code expires in {settings.otp_expiry_minutes} minutes. If you did not request it, you can ignore this email."
    html = (
        f"<p>Use this code to {escape(action)}:</p>"
        f"<p style='font-size:28px;font-weight:bold;letter-spacing:6px'>{escape(code or '')}</p>"
        f"<p>The code expires in {settings.otp_expiry_minutes} minutes. If you did not request it, ignore this email.</p>"
    )
    return plain, html


class EmailProvider(Protocol):
    def send(self, to_email: str, subject: str, plain: str, html: str) -> None: ...


class ConsoleEmailProvider:
    def send(self, to_email: str, subject: str, plain: str, html: str) -> None:
        del subject, html
        logger.info("AURA email to %s:\n%s", to_email, plain)


class SmtpEmailProvider:
    def send(self, to_email: str, subject: str, plain: str, html: str) -> None:
        if not settings.smtp_host:
            raise RuntimeError("SMTP_HOST is required when EMAIL_PROVIDER=smtp")
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.email_from
        message["To"] = to_email
        message.set_content(plain)
        message.add_alternative(html, subtype="html")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as client:
            client.starttls()
            if settings.smtp_username:
                client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)


def send_email(to_email: str, kind: EmailKind, code: str | None = None) -> None:
    plain, html = _content(kind, code)
    provider: EmailProvider = ConsoleEmailProvider() if settings.email_provider == "console" else SmtpEmailProvider()
    provider.send(to_email, SUBJECTS[kind], plain, html)


def send_email_safely(to_email: str, kind: EmailKind, code: str | None = None) -> None:
    try:
        send_email(to_email, kind, code)
    except Exception as error:
        # Do not log SMTP credentials or message content on provider failures.
        logger.error("Failed to send AURA email (%s) to %s; error_type=%s", kind, to_email, type(error).__name__)
