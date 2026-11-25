from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = SERVER_DIR / "static"
ASSETS_DIR = STATIC_DIR / "assets"
UPLOADS_DIR = STATIC_DIR / "uploads"
ADMIN_DIR = SERVER_DIR / "admin"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=SERVER_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str = "postgresql+psycopg://localhost/linghuali"
    JWT_SECRET: str = "change-me"
    JWT_EXPIRE_DAYS: int = 30
    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""
    WECHAT_MOCK_LOGIN: bool = True
    ASSET_BASE_URL: str = "http://127.0.0.1:8001/static/assets/"
    UPLOAD_BASE_URL: str = "http://127.0.0.1:8001/static/uploads/"
    ADMIN_TOKEN: str = ""
    # Comma separated list, or "*".
    CORS_ORIGINS: str = "*"

    @field_validator("ASSET_BASE_URL", "UPLOAD_BASE_URL")
    @classmethod
    def _trailing_slash(cls, v: str) -> str:
        return v if v.endswith("/") else v + "/"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()] or ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
