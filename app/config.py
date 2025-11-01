import os
from typing import Any


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


class Settings:
    """
    Простая замена pydantic BaseSettings — читает прямо из окружения.
    По умолчанию WEBAPP_BASE_URL указывает на публичный HTTPS URL Render (index.html).
    """
    def __init__(self) -> None:
        self.BOT_TOKEN: str | None = os.getenv("BOT_TOKEN") or None
        # Публичный HTTPS URL по умолчанию — безопасно для Telegram WebApp
        self.WEBAPP_BASE_URL: str = os.getenv(
            "WEBAPP_BASE_URL",
            "https://miniapp-tg-uubc.onrender.com/webapp/index.html",
        )
        self.USE_JWT: bool = _coerce_bool(os.getenv("USE_JWT"))
        self.JWT_SECRET: str | None = os.getenv("JWT_SECRET") or None


# единственный экземпляр настроек, импортируется остальным кодом как `settings`
settings = Settings()