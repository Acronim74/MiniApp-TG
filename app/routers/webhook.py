from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import requests
import logging
import json
from ..config import settings

router = APIRouter()
logger = logging.getLogger("app.webhook")


@router.post("/webhook")
async def telegram_webhook(req: Request):
    """
    Telegram webhook with extra debug logging:
    - logs incoming update JSON
    - logs full Telegram response body if sendMessage fails
    """
    try:
        update = await req.json()
    except Exception as e:
        logger.exception("Failed to parse incoming webhook JSON: %s", e)
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)

    # Log the raw update for debugging (remove or reduce in production)
    try:
        logger.info("Incoming update: %s", json.dumps(update, ensure_ascii=False))
    except Exception:
        logger.info("Incoming update (repr): %s", repr(update))

    # Try to extract chat and user info
    message = update.get("message") or update.get("edited_message") or {}
    from_user = message.get("from") or {}
    chat = message.get("chat") or {}

    telegram_id = from_user.get("id") or chat.get("id")
    if not telegram_id:
        logger.warning("No chat id found in update; nothing to send. Update keys: %s", list(update.keys()))
        return JSONResponse({"ok": True})

    webapp_url = settings.WEBAPP_BASE_URL

    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "Open WebApp",
                    "web_app": {"url": webapp_url}
                }
            ]
        ]
    }

    text = "Откройте WebApp, чтобы продолжить (в нем будет использован Telegram initData для безопасного входа)."

    if not settings.BOT_TOKEN:
        logger.warning("BOT_TOKEN not set; built url: %s", webapp_url)
        return JSONResponse({"ok": True, "webapp_url": webapp_url})

    send_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": telegram_id, "text": text, "reply_markup": reply_markup}

    try:
        resp = requests.post(send_url, json=payload, timeout=10)
        if not resp.ok:
            # Log full response body from Telegram for diagnosis
            logger.error("Telegram API error: status=%s body=%s", resp.status_code, resp.text)
            logger.debug("Payload sent to Telegram: %s", json.dumps(payload, ensure_ascii=False))
            # do not raise here — returning ok to webhook so Telegram won't retry too aggressively
            return JSONResponse({"ok": True})
        logger.info("Sent WebApp button to chat_id=%s", telegram_id)
    except Exception as e:
        logger.exception("Failed to send message to Telegram: %s", e)
    return JSONResponse({"ok": True})