from dataclasses import dataclass

from google.auth.transport import requests
from google.oauth2 import id_token as google_id_token

from app.core.config import settings


class GoogleTokenError(Exception):
    pass


@dataclass(frozen=True)
class GoogleUserInfo:
    sub: str
    email: str
    email_verified: bool
    name: str


def verify_google_id_token(token: str) -> GoogleUserInfo:
    if not settings.google_client_id:
        raise GoogleTokenError("Login com Google nao configurado.")

    try:
        payload = google_id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        raise GoogleTokenError("Token Google invalido.") from exc

    issuer = payload.get("iss")
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        raise GoogleTokenError("Token Google invalido.")

    sub = payload.get("sub")
    email = payload.get("email")
    email_verified = payload.get("email_verified")
    if not sub or not email:
        raise GoogleTokenError("Token Google sem dados obrigatorios.")
    if email_verified is not True:
        raise GoogleTokenError("E-mail Google nao verificado.")

    return GoogleUserInfo(
        sub=str(sub),
        email=str(email),
        email_verified=True,
        name=str(payload.get("name") or email.split("@", 1)[0]),
    )
