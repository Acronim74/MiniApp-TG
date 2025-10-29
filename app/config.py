# app/config.py
# Более робастная загрузка настроек: пытаемся создать класс Settings (pydantic),
# но при ошибках делаем явную коэрцировку значений окружения (особенно USE_JWT).
import os
from typing import Any

# Try to import BaseSettings from pydantic or pydantic-settings (compat)
try:
    from pydantic import BaseSettings
except Exception:
    from pydantic_settings import BaseSettings

from pydantic import ValidationError


def _coerce_bool(value: Any) -> bool:
    """
    Robust coercion of common truthy/falsy string values to bool.
    Accepts booleans directly, numeric strings, and common words.
    Fallback: False.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    v = str(value).strip().lower()
    if v in {"1", "true", "yes", "on"}:
        return True
    if v in {"0", "false", "no", "off", ""}:
        return False
    # If it's some placeholder like "true|false" treat as False (safe default)
    return False


class Settings(BaseSettings):
    BOT_TOKEN: str | None = None
    WEBAPP_BASE_URL: str = "http://127.0.0.1:8000/webapp"
    USE_JWT: bool = False
    JWT_SECRET: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def _load_settings_fallback() -> Settings:
    """
    Manual fallback: read env vars and coerce types, then instantiate Settings
    using explicit values to avoid ValidationError on env parsing.
    """
    bot = os.getenv("BOT_TOKEN") or None
    webapp = os.getenv("WEBAPP_BASE_URL") or "http://127.0.0.1:8000/webapp"
    use_jwt_raw = os.getenv("USE_JWT")
    use_jwt = _coerce_bool(use_jwt_raw)
    jwt_secret = os.getenv("JWT_SECRET") or None

    return Settings(
        BOT_TOKEN=bot,
        WEBAPP_BASE_URL=webapp,
        USE_JWT=use_jwt,
        JWT_SECRET=jwt_secret,
    )


# Try normal Settings() first; if ValidationError occurs (e.g. bad env values),
# fall back to manual coercion.
try:
    settings = Settings()
except ValidationError:
    # Optionally, log the error to stdout/stderr in real deployments
    settings = _load_settings_fallback()