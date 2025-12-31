from pydantic_settings import BaseSettings
from pathlib import Path
from urllib.parse import quote_plus
from typing import List
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = 'Travel Master'
    FRONTEND_URL: str = 'http://localhost:1598'
    PORT: int = 8003
    SERVER_HOST: str = '0.0.0.0'
    WORKERS: int = 4
    PY_ENV: str = "development"

    # Railway / Prod
    DATABASE_PUBLIC_URL: str | None = None

    # Local DB (fallback)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASS: str = "test123"
    DB_NAME: str = "app_db"

    # CORS
    ALLOW_ORIGINS: str = "*"
    ALLOW_CREDENTIALS: bool = False
    ALLOW_METHODS: str = "*"
    ALLOW_HEADERS: str = "*"

    # JWT
    JWT_SECRET_KEY: str = "c1kTe2nX1l0GluxA6L15C0E0f5eYAgOc3jxk0neCkE"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES: int = 52560000 # 100 years = 100 * 365 * 24 * 60 minutes

    @property
    def SQLALCHEMY_DB_URL(self) -> str:
        """Prefer Railway DATABASE_URL, fallback to local config"""
        if self.DATABASE_PUBLIC_URL:
            # SQLAlchemy 1.4+ and 2.0 require 'postgresql://' instead of 'postgres://'
            url = self.DATABASE_PUBLIC_URL
            print(url)
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            
            # Ensure the driver is specified if not present
            if "postgresql://" in url and "postgresql+psycopg2://" not in url:
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            
            return url

        return (
            f"postgresql+psycopg2://{self.DB_USER}:{quote_plus(self.DB_PASS)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME if hasattr(self, 'DB_NAME') else 'app_db'}"
        )
    @property
    def ALLOW_ORIGINS_LIST(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOW_ORIGINS.split(",")]
      
    @property
    def ALLOW_METHODS_LIST(self) -> List[str]:
        return [method.strip() for method in self.ALLOW_METHODS.split(",")]
    @property
    def ALLOW_HEADERS_LIST(self) -> List[str]:
        return [header.strip() for header in self.ALLOW_HEADERS.split(",")]
      
    @property
    def IS_DEV(self) -> bool:
        return self.PY_ENV.lower() == "development"
    @property
    def IS_PROD(self) -> bool:
        return not self.IS_DEV
    # SMTP
    SMTP_USERNAME: str = "info@travelmaster.com"
    SMTP_PASSWORD: str = "J{=#KUjH]P7X@7^4"
    SMTP_PORT: int = 465
    SMTP_HOSTNAME: str = "mail.travelmaster.com"
    SMTP_TLS: str = ""
    MAIL_FROM_NAME: str = "Travel Master"
    # GCS
    GCS_BUCKET_NAME: str = "tm_images"
    GCS_TYPE: str | None = None
    GCS_PROJECT_ID: str | None = None
    GCS_PRIVATE_KEY_ID: str | None = None
    GCS_PRIVATE_KEY: str | None = None
    GCS_CLIENT_EMAIL: str | None = None
    GCS_CLIENT_ID: str | None = None
    GCS_AUTH_URI: str | None = None
    GCS_TOKEN_URI: str | None = None
    GCS_AUTH_PROVIDER_X509_CERT_URL: str | None = None
    GCS_CLIENT_X509_CERT_URL: str | None = None
    GCS_UNIVERSE_DOMAIN: str | None = None

    MAIL_FROM_EMAIL: str = "info@travelmaster.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        env_prefix = ""
        case_sensitive = True


settings = Settings()
