from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gestão Financeira Empresarial"
    app_env: str = "local"
    app_debug: bool = True
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    frontend_url: str = "http://localhost:5173"
    email_delivery_mode: str = "mock"
    email_from: str = "no-reply@example.com"
    email_from_name: str = "Gestao Financeira Empresarial"
    email_verification_token_expire_minutes: int = 60
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_timeout_seconds: int = 20
    brevo_api_key: str = ""
    brevo_api_key_file: str = ""
    brevo_api_url: str = "https://api.brevo.com/v3/smtp/email"
    google_client_id: str = ""

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.app_env.lower() == "production":
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production")
            if len(self.jwt_secret_key.strip()) < 32:
                raise ValueError("JWT_SECRET_KEY must have at least 32 characters in production")
            if "*" in self.cors_origins_list:
                raise ValueError("BACKEND_CORS_ORIGINS cannot include '*' in production")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
