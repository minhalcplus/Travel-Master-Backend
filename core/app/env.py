from pydantic_settings import BaseSettings
from pathlib import Path
from urllib.parse import quote_plus
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    APP_NAME: str = 'Travel Master'
    FRONTEND_URL: str = 'http://localhost:1598'
    PORT: int = 8002
    SERVER_HOST: str = '0.0.0.0'
    WORKERS: int = 4
    PY_ENV:str = "development"

    # DB SETTINGS
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASS: str = "test123"
    DB_NAME: str = "app_db"
    
    # CORS Configuration
    ALLOW_ORIGINS: str = "http://localhost:8000"
    ALLOW_CREDENTIALS: bool = True
    ALLOW_METHODS: str = "GET,POST,PUT,DELETE"
    ALLOW_HEADERS: str = "*"


    # JWT
    JWT_SECRET_KEY: str = "c1kTe2nX1l0GluxA6L15C0E0f5eYAgOc3jxk0neCkE"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES: int = 30
    #google oauth setup
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    
    @property
    def SQLALCHEMY_DB_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{quote_plus(self.DB_PASS)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
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
        """Returns True if PY_ENV is set to 'development' (case-insensitive)"""
        return self.PY_ENV.lower() == "development"
    @property
    def IS_PROD(self) -> bool:
        """Returns True if not in development mode"""
        return not self.IS_DEV
    # SMTP
    SMTP_USERNAME: str = "info@travelmaster.com"
    SMTP_PASSWORD: str = "J{=#KUjH]P7X@7^4"
    SMTP_PORT: int = 465
    SMTP_HOSTNAME: str = "mail.travelmaster.com"
    SMTP_TLS: str = ""
    MAIL_FROM_NAME: str = "Travel Master"
    MAIL_FROM_EMAIL: str = "info@travelmaster.com"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        env_prefix = ""
        case_sensitive = True


settings = Settings()
