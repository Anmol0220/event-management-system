from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Event Management System"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True
    show_docs: bool = True

    secret_key: str = Field(
        default="change-this-secret-key-before-production-please",
        min_length=32,
    )
    csrf_secret_key: str = Field(
        default="change-this-csrf-secret-before-production-please",
        min_length=32,
    )
    allow_open_admin_signup: bool = False
    admin_signup_code: str | None = None
    session_cookie_name: str = "ems_session"
    session_max_age: int = 60 * 60 * 8
    session_https_only: bool = False
    session_same_site: Literal["lax", "strict", "none"] = "lax"
    product_image_max_size_bytes: int = 2 * 1024 * 1024
    log_level: str = "INFO"
    log_sql_queries: bool = False

    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "event_management"
    database_user: str = "postgres"
    database_password: str = "postgres"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @computed_field
    @property
    def effective_session_https_only(self) -> bool:
        return self.session_https_only or self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()
