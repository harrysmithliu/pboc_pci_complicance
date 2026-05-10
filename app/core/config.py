from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Payment Compliance MVP"
    app_env: str = "local"
    debug: bool = True

    database_url: str = "sqlite:///./payment_compliance.db"

    jwt_secret_key: str = "change-me-local-jwt-secret"
    jwt_expires_minutes: int = 60

    seed_admin_username: str = "admin"
    seed_admin_password: str = "admin123"
    seed_operator_username: str = "operator"
    seed_operator_password: str = "operator123"
    seed_auditor_username: str = "auditor"
    seed_auditor_password: str = "auditor123"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

