from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import requests
import logging
from ..config import settings

router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(req: Request):
    """
    Minimal Telegram webhook that sends an InlineKeyboard button
    opening the WebApp. The WebApp obtains initData from Telegram client
    and posts it to /auth/init for server verification.
    """
    try:
        update = await req.json()
    except Exception as e:
        logging.exception("Failed to parse incoming webhook JSON: %s", e)
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)

    message = update.get("message") or update.get("edited_message") or {}
    from_user = message.get("from") or {}
    chat_id = message.get("chat", {}).get("id") or from_user.get("id")

    if not chat_id:
        return JSONResponse({"ok": True})

    # Build web_app button URL (no query params — client will provide initData)
    webapp_url = settings.WEBAPP_BASE_URL

    # reply markup with web_app button
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
        logging.warning("BOT_TOKEN not set; built url: %s", webapp_url)
        return JSONResponse({"ok": True, "webapp_url": webapp_url})

    send_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "reply_markup": reply_markup}

    try:
        resp = requests.post(send_url, json=payload, timeout=10)
        resp.raise_for_status()
        logging.info("Sent WebApp button to chat_id=%s", chat_id)
    except Exception as e:
        logging.exception("Failed to send message to Telegram: %s", e)

    return JSONResponse({"ok": True})