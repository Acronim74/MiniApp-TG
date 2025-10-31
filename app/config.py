import os
from typing import Any

from pydantic import BaseSettings, ValidationError

def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    v = str(value).strip().lower()
    if v in {"1", "true", "yes", "on"}:
        return True
    if v in {"0", "false", "no", "off", ""}:
        return False
    return False


class Settings(BaseSettings):
    BOT_TOKEN: str | None = None
    # Заменён дефолт на публичный HTTPS URL Render (index.html)
    WEBAPP_BASE_URL: str = "https://miniapp-tg-uubc.onrender.com/webapp/index.html"
    USE_JWT: bool = False
    JWT_SECRET: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def _load_settings_fallback() -> Settings:
    bot = os.getenv("BOT_TOKEN") or None
    webapp = os.getenv("WEBAPP_BASE_URL") or "https://miniapp-tg-uubc.onrender.com/webapp/index.html"
    use_jwt_raw = os.getenv("USE_JWT")
    use_jwt = _coerce_bool(use_jwt_raw)
    jwt_secret = os.getenv("JWT_SECRET") or None

    return Settings(
        BOT_TOKEN=bot,
        WEBAPP_BASE_URL=webapp,
        USE_JWT=use_jwt,
        JWT_SECRET=jwt_secret,
    )


try:
    settings = Settings()
except ValidationError:
    settings = _load_settings_fallback()