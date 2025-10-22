from fastapi import APIRouter, HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from ..config import settings
from ..utils.telegram_auth import verify_init_data
import logging
import time
from jose import jwt

router = APIRouter()


@router.post("/auth/init")
async def auth_init(req: Request):
    """
    Accepts JSON:
      { "init_data": "<init_data_string_from_telegram>" }

    Validates init_data using BOT_TOKEN. If valid:
      - if USE_JWT == true and JWT_SECRET set -> returns {"ok": True, "user": {...}, "token": "<jwt>"}
      - otherwise returns {"ok": True, "user": {...}}

    In case of invalid init_data return 400.
    """
    body = await req.json()
    init_data = body.get("init_data")
    if not init_data:
        raise HTTPException(status_code=400, detail="init_data required")

    if not settings.BOT_TOKEN:
        logging.warning("BOT_TOKEN not configured; rejecting init_data")
        raise HTTPException(status_code=500, detail="server misconfiguration")

    ok, payload_or_err = verify_init_data(init_data, settings.BOT_TOKEN)
    if not ok:
        logging.warning("init_data verification failed: %s", payload_or_err)
        raise HTTPException(status_code=400, detail="init_data invalid")

    # payload_or_err is dict of fields from init_data (without hash)
    user = {
        "id": payload_or_err.get("id"),
        "username": payload_or_err.get("username"),
        "first_name": payload_or_err.get("first_name"),
        "auth_date": payload_or_err.get("auth_date"),
    }

    result = {"ok": True, "user": user}

    if settings.USE_JWT:
        if not settings.JWT_SECRET:
            logging.error("USE_JWT enabled but JWT_SECRET not set")
            raise HTTPException(status_code=500, detail="server misconfiguration")
        now = int(time.time())
        token = jwt.encode({"sub": str(user["id"]), "iat": now, "exp": now + 3600}, settings.JWT_SECRET, algorithm="HS256")
        result["token"] = token

    return JSONResponse(result)