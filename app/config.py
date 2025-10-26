try:
    # pydantic v1 поддерживал BaseSettings внутри pydantic
    from pydantic import BaseSettings
except Exception:
    # В pydantic v2 BaseSettings вынесен в отдельный пакет pydantic-settings
    from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str | None = None
    WEBAPP_BASE_URL: str = "http://127.0.0.1:8000/webapp"
    USE_JWT: bool = False
    JWT_SECRET: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()