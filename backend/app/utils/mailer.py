import os
import logging
from email.message import EmailMessage
import smtplib

logger = logging.getLogger(__name__)


def _get_env(name: str, default=None):
    return os.getenv(name, default)


def send_email(subject: str, body: str, recipient: str) -> None:
    """Send a simple text email using SMTP env vars.

    Required env vars (recommended):
      MAIL_HOST, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM

    If `MAIL_HOST` is not set the function will log and return without error.
    """
    mail_host = _get_env("MAIL_HOST")
    if not mail_host:
        logger.info("Mail not configured (MAIL_HOST missing) — skipping send_email")
        return

    mail_port = int(_get_env("MAIL_PORT", "587"))
    mail_user = _get_env("MAIL_USERNAME")
    mail_pass = _get_env("MAIL_PASSWORD")
    mail_from = _get_env("MAIL_FROM", mail_user or "no-reply@example.com")
    use_tls = _get_env("MAIL_USE_TLS", "true").lower() in {"1", "true", "yes"}

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = recipient
    msg.set_content(body)

    try:
        if use_tls:
            server = smtplib.SMTP(mail_host, mail_port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(mail_host, mail_port, timeout=10)

        if mail_user and mail_pass:
            server.login(mail_user, mail_pass)

        server.send_message(msg)
        server.quit()
        logger.info(f"Email sent to {recipient} (subject={subject})")
    except Exception:
        logger.exception("Failed to send email")
        raise
