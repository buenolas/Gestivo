from functools import lru_cache

from pydantic import field_validator
from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Gestão Financeira Empresarial"
    app_env: str = "local"
    app_debug: bool = True
    database_url: str
    migration_database_url: str = ""
    jwt_secret_key: str
    cron_secret: str = ""
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

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def normalize_postgresql_driver(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    @field_validator("email_delivery_mode")
    @classmethod
    def validate_email_delivery_mode(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        allowed_modes = {"mock", "smtp", "brevo_api"}
        if normalized_value not in allowed_modes:
            raise ValueError(
                "EMAIL_DELIVERY_MODE must be one of: mock, smtp, brevo_api"
            )
        return normalized_value

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.app_env.lower() == "production":
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production")
            if len(self.jwt_secret_key.strip()) < 32:
                raise ValueError("JWT_SECRET_KEY must have at least 32 characters in production")
            if len(self.cron_secret.strip()) < 32:
                raise ValueError("CRON_SECRET must have at least 32 characters in production")
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

    @property
    def alembic_database_url(self) -> str:
        return self.migration_database_url.strip() or self.database_url

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
