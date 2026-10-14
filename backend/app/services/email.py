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
    _send_access_email(email, verification_link, invitation=False)


def send_company_user_invitation(email: str, invitation_link: str) -> None:
    _send_access_email(email, invitation_link, invitation=True)


def _send_access_email(email: str, link: str, *, invitation: bool) -> None:
    if settings.email_delivery_mode == "mock":
        logger.warning(
            "Mock access e-mail generated for %s. Token omitted from logs.",
            email,
        )
        return

    if settings.email_delivery_mode == "smtp":
        send_email_verification_smtp(email, link, invitation=invitation)
        return

    if settings.email_delivery_mode == "brevo_api":
        send_email_verification_brevo_api(email, link, invitation=invitation)
        return

    raise EmailDeliveryError("Email delivery mode is not configured")


def send_password_reset_code(email: str, code: str) -> None:
    if settings.email_delivery_mode == "mock":
        logger.warning(
            "Mock password reset code generated for %s. Code omitted from logs.",
            email,
        )
        return

    if settings.email_delivery_mode == "smtp":
        send_password_reset_code_smtp(email, code)
        return

    if settings.email_delivery_mode == "brevo_api":
        send_password_reset_code_brevo_api(email, code)
        return

    raise EmailDeliveryError("Email delivery mode is not configured")


def send_email_verification_smtp(
    email: str,
    verification_link: str,
    *,
    invitation: bool = False,
) -> None:
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        raise EmailDeliveryError("SMTP delivery is missing required configuration")

    message = EmailMessage()
    message["Subject"] = "Convite de acesso ao Gestivo" if invitation else "Confirme seu e-mail"
    message["From"] = f"{settings.email_from_name} <{settings.email_from}>"
    message["To"] = email
    text_content = (
        invitation_text(verification_link)
        if invitation
        else "\n".join(
            [
                "Confirme seu e-mail para liberar o acesso financeiro.",
                "",
                f"Acesse o link: {verification_link}",
                "",
                "Se voce nao criou uma conta, ignore esta mensagem.",
            ],
        )
    )
    html_content = invitation_html(verification_link) if invitation else f"""
        <html>
          <body>
            <p>Confirme seu e-mail para liberar o acesso financeiro.</p>
            <p><a href="{verification_link}">Confirmar e-mail</a></p>
            <p>Se voce nao criou uma conta, ignore esta mensagem.</p>
          </body>
        </html>
        """
    message.set_content(text_content)
    message.add_alternative(
        html_content,
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
        message_error = (
            "Nao foi possivel enviar o convite de acesso"
            if invitation
            else "Nao foi possivel enviar o e-mail de verificacao"
        )
        raise EmailDeliveryError(message_error) from exc


def send_password_reset_code_smtp(email: str, code: str) -> None:
    if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
        raise EmailDeliveryError("SMTP delivery is missing required configuration")

    message = EmailMessage()
    message["Subject"] = "Codigo para redefinir sua senha"
    message["From"] = f"{settings.email_from_name} <{settings.email_from}>"
    message["To"] = email
    message.set_content(password_reset_text(code))
    message.add_alternative(password_reset_html(code), subtype="html")

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
        raise EmailDeliveryError("Nao foi possivel enviar o codigo de recuperacao") from exc


def send_email_verification_brevo_api(
    email: str,
    verification_link: str,
    *,
    invitation: bool = False,
) -> None:
    api_key = brevo_api_key()
    if not api_key:
        raise EmailDeliveryError("Brevo API delivery is missing required configuration")

    payload = {
        "sender": {
            "name": settings.email_from_name,
            "email": settings.email_from,
        },
        "to": [{"email": email}],
        "subject": (
            "Convite de acesso ao Gestivo"
            if invitation
            else "Confirme seu e-mail"
        ),
        "textContent": (
            invitation_text(verification_link)
            if invitation
            else verification_text(verification_link)
        ),
        "htmlContent": (
            invitation_html(verification_link)
            if invitation
            else verification_html(verification_link)
        ),
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
        message_error = (
            "Nao foi possivel enviar o convite de acesso"
            if invitation
            else "Nao foi possivel enviar o e-mail de verificacao"
        )
        raise EmailDeliveryError(message_error) from exc


def invitation_text(invitation_link: str) -> str:
    return "\n".join(
        [
            "Voce recebeu um convite para acessar uma empresa no Gestivo.",
            "Confirme seu e-mail e crie uma senha para ativar o acesso:",
            "",
            invitation_link,
            "",
            "Se voce nao esperava este convite, ignore esta mensagem.",
        ],
    )


def invitation_html(invitation_link: str) -> str:
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #111827; line-height: 1.5;">
        <h1 style="font-size: 20px;">Convite de acesso ao Gestivo</h1>
        <p>Voce recebeu um convite para acessar uma empresa no Gestivo.</p>
        <p>Confirme seu e-mail e crie uma senha para ativar o acesso.</p>
        <p style="margin: 24px 0;">
          <a href="{invitation_link}" style="background: #0F3D4A; color: #ffffff; padding: 12px 18px; text-decoration: none; border-radius: 6px; display: inline-block;">
            Confirmar e criar senha
          </a>
        </p>
        <p style="font-size: 13px; color: #667085;">Se voce nao esperava este convite, ignore esta mensagem.</p>
      </body>
    </html>
    """


def send_password_reset_code_brevo_api(email: str, code: str) -> None:
    api_key = brevo_api_key()
    if not api_key:
        raise EmailDeliveryError("Brevo API delivery is missing required configuration")

    payload = {
        "sender": {
            "name": settings.email_from_name,
            "email": settings.email_from,
        },
        "to": [{"email": email}],
        "subject": "Codigo para redefinir sua senha",
        "textContent": password_reset_text(code),
        "htmlContent": password_reset_html(code),
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
        raise EmailDeliveryError("Nao foi possivel enviar o codigo de recuperacao") from exc


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


def password_reset_text(code: str) -> str:
    return "\n".join(
        [
            "Redefinicao de senha",
            "",
            "Recebemos uma solicitacao para redefinir sua senha no Gestivo.",
            f"Use este codigo para continuar: {code}",
            "",
            "Este codigo expira em breve. Se voce nao solicitou a redefinicao, ignore esta mensagem.",
        ],
    )


def password_reset_html(code: str) -> str:
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #111827; line-height: 1.5;">
        <h1 style="font-size: 20px;">Redefinicao de senha</h1>
        <p>Recebemos uma solicitacao para redefinir sua senha no Gestivo.</p>
        <p>Use este codigo para continuar:</p>
        <p style="font-size: 28px; font-weight: 700; letter-spacing: 4px; color: #0F3D4A;">
          {code}
        </p>
        <p style="font-size: 13px; color: #667085;">
          Este codigo expira em breve. Se voce nao solicitou a redefinicao, ignore esta mensagem.
        </p>
      </body>
    </html>
    """
