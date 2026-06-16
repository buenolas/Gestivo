import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    pass


def send_email_verification(email: str, verification_link: str) -> None:
    if settings.email_delivery_mode == "mock":
        logger.warning(
            "Mock email verification generated for %s. Token omitted from logs.",
            email,
        )
        return

    if settings.email_delivery_mode == "smtp":
        send_email_verification_smtp(email, verification_link)
        return

    if settings.email_delivery_mode == "brevo_api":
        send_email_verification_brevo_api(email, verification_link)
        return

    raise EmailDeliveryError("Email delivery mode is not configured")


def send_email_verification_smtp(email: str, verification_link: str) -> None:
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        raise EmailDeliveryError("SMTP delivery is missing required configuration")

    message = EmailMessage()
    message["Subject"] = "Confirme seu e-mail"
    message["From"] = f"{settings.email_from_name} <{settings.email_from}>"
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                "Confirme seu e-mail para liberar o acesso financeiro.",
                "",
                f"Acesse o link: {verification_link}",
                "",
                "Se voce nao criou uma conta, ignore esta mensagem.",
            ],
        ),
    )
    message.add_alternative(
        f"""
        <html>
          <body>
            <p>Confirme seu e-mail para liberar o acesso financeiro.</p>
            <p><a href="{verification_link}">Confirmar e-mail</a></p>
            <p>Se voce nao criou uma conta, ignore esta mensagem.</p>
          </body>
        </html>
        """,
        subtype="html",
    )

    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Nao foi possivel enviar o e-mail de verificacao") from exc


def send_email_verification_brevo_api(email: str, verification_link: str) -> None:
    api_key = brevo_api_key()
    if not api_key:
        raise EmailDeliveryError("Brevo API delivery is missing required configuration")

    payload = {
        "sender": {
            "name": settings.email_from_name,
            "email": settings.email_from,
        },
        "to": [{"email": email}],
        "subject": "Confirme seu e-mail",
        "textContent": verification_text(verification_link),
        "htmlContent": verification_html(verification_link),
    }
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    try:
        response = requests.post(
            settings.brevo_api_url,
            json=payload,
            headers=headers,
            timeout=settings.smtp_timeout_seconds,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise EmailDeliveryError("Nao foi possivel enviar o e-mail de verificacao") from exc


def brevo_api_key() -> str:
    if settings.brevo_api_key:
        return settings.brevo_api_key.strip()
    if settings.brevo_api_key_file:
        return Path(settings.brevo_api_key_file).read_text(encoding="utf-8").strip()
    return ""


def verification_text(verification_link: str) -> str:
    return "\n".join(
        [
            "Confirme seu e-mail",
            "",
            "Recebemos um cadastro para o Gestivo usando este e-mail.",
            "Para liberar o acesso aos recursos financeiros da sua empresa, confirme seu e-mail no link abaixo:",
            "",
            verification_link,
            "",
            "Este link expira em breve. Se voce nao criou uma conta, ignore esta mensagem.",
        ],
    )


def verification_html(verification_link: str) -> str:
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #111827; line-height: 1.5;">
        <h1 style="font-size: 20px;">Confirme seu e-mail</h1>
        <p>
          Recebemos um cadastro para o Gestivo usando este e-mail.
        </p>
        <p>
          Para liberar o acesso aos recursos financeiros da sua empresa, confirme seu e-mail.
        </p>
        <p style="margin: 24px 0;">
          <a
            href="{verification_link}"
            style="background: #0F3D4A; color: #ffffff; padding: 12px 18px; text-decoration: none; border-radius: 6px; display: inline-block;"
          >
            Confirmar e-mail
          </a>
        </p>
        <p style="font-size: 13px; color: #667085;">
          Este link expira em breve. Se voce nao criou uma conta, ignore esta mensagem.
        </p>
      </body>
    </html>
    """
