from pydantic_settings import BaseSettings
from typing import Optional
import os


import os

_env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "GameAssistant API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DB_URL: str = "mysql+aiomysql://gameassistant:gameassistant@mysql:3306/gameassistant"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # JWT
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Admin user (auto-created on startup)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_EMAIL: str = "admin@gameassistant.local"

    # File Storage
    UPLOAD_DIR: str = "/app/uploads"
    TEMPLATE_DIR: str = "/app/templates"
    MODEL_DIR: str = "/app/models"
    MAX_UPLOAD_SIZE: int = 2 * 1024 * 1024 * 1024  # 2GB

    # ADB
    ADB_HOST: str = "localhost"
    ADB_PORT: int = 5037

    class Config:
        env_file = _env_file
        case_sensitive = True
        extra = "ignore"

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Parse CORS_ORIGINS from environment, supporting comma-separated string."""
        raw = os.environ.get("CORS_ORIGINS", "")
        if raw:
            return [v.strip() for v in raw.split(",") if v.strip()]
        return ["http://localhost:3000", "http://localhost:8080"]


settings = Settings()

# Ensure directories exist
for dir_path in [settings.UPLOAD_DIR, settings.TEMPLATE_DIR, settings.MODEL_DIR]:
    os.makedirs(dir_path, exist_ok=True)
