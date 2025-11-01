"""
Utilities to verify Telegram WebApp initData per Telegram docs.

This implementation is tolerant to a few common variants:
- init_data = "query_id=...&user=...&hash=..."
- init_data = "tgWebAppData=query_id%3D...%26user%3D...%26hash%3D..." (wrapper)
- init_data = "query_id%3D...%26user%3D...%26hash%3D..." (raw percent-encoded fragment)

We attempt verification on several normalized forms until one succeeds.
"""
from typing import Tuple, Dict, Any
import hashlib
import hmac
import urllib.parse
import logging

logger = logging.getLogger("app.telegram_auth")


def parse_init_data(init_data: str) -> Dict[str, str]:
    # parse like query string (does not decode percent-encoded separators)
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    return parsed


def _try_parse_variants(init_data: str) -> Tuple[Dict[str, str], str]:
    """
    Try different normalization variants and return (parsed_dict, variant_name)
    variant_name is one of: "raw", "unquote_once", "unquote_twice", "tgWebAppData_inner"
    If none parsed to include a 'hash' key, returns (parsed_from_last_attempt, last_variant_name).
    """
    # 1) try raw
    parsed = parse_init_data(init_data)
    if "hash" in parsed:
        return parsed, "raw"

    # 2) if top-level has tgWebAppData key (like tgWebAppData=percent-encoded...), decode inner
    if "tgWebAppData" in parsed:
        try:
            inner = urllib.parse.unquote(parsed["tgWebAppData"])
            parsed_inner = parse_init_data(inner)
            if "hash" in parsed_inner:
                return parsed_inner, "tgWebAppData_inner"
            # fallthrough: keep parsed_inner as candidate
            parsed = parsed_inner
            variant = "tgWebAppData_inner"
        except Exception:
            variant = "tgWebAppData_inner_failed"
    else:
        variant = "raw"

    # 3) try unquote once if raw looks percent-encoded (contains %3D or %26)
    low = init_data.lower()
    if "%3d" in low or "%26" in low or "%7b" in low or "%7b" in low:
        try:
            un1 = urllib.parse.unquote(init_data)
            parsed_un1 = parse_init_data(un1)
            if "hash" in parsed_un1:
                return parsed_un1, "unquote_once"
            parsed = parsed_un1
            variant = "unquote_once"
        except Exception:
            pass

    # 4) try unquote twice (some clients double-encode)
    try:
        un2 = urllib.parse.unquote(urllib.parse.unquote(init_data))
        parsed_un2 = parse_init_data(un2)
        if "hash" in parsed_un2:
            return parsed_un2, "unquote_twice"
        parsed = parsed_un2
        variant = "unquote_twice"
    except Exception:
        pass

    return parsed, variant


def verify_init_data(init_data: str, bot_token: str) -> Tuple[bool, Dict[str, Any] | str]:
    """
    Returns (True, payload_dict_without_hash) if verification succeeded,
    otherwise (False, error_message).
    """
    if not isinstance(init_data, str):
        return False, "init_data not a string"

    # Try parsing multiple normalized variants to find "hash"
    parsed, used_variant = _try_parse_variants(init_data)

    # If we ended up with tgWebAppData wrapper decoded into parsed, init_data variable should reflect the inner payload for later logging
    if used_variant == "tgWebAppData_inner":
        try:
            # decode once to update init_data used in logs
            init_data = urllib.parse.unquote(init_data) if "tgWebAppData=" in init_data else init_data
        except Exception:
            pass

    provided_hash = parsed.pop("hash", None)
    if not provided_hash:
        # Log raw input and parsed keys to aid debugging
        try:
            logger.warning("init_data verification failed: no hash in init_data (variant tried: %s)", used_variant)
            logger.warning("init_data (raw): %s", init_data)
            logger.warning("parsed keys: %s", list(parsed.keys()))
        except Exception:
            logger.exception("Failed while logging debug info for missing hash")
        return False, "no hash in init_data"

    # build data_check_string as Telegram requires (sorted keys joined by \n)
    items = []
    for k in sorted(parsed.keys()):
        items.append(f"{k}={parsed[k]}")
    data_check_string = "\n".join(items)

    # secret key is SHA256 of bot_token
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()

    # compute HMAC-SHA256
    hmac_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(hmac_hash, provided_hash):
        # Detailed debug logging to diagnose mismatch
        try:
            logger.warning("init_data verification failed: hash_mismatch (variant tried: %s)", used_variant)
            logger.warning("init_data (raw): %s", init_data)
            logger.warning("parsed fields: %s", parsed)
            logger.warning("data_check_string: %s", data_check_string)
            logger.warning("secret_key (SHA256(bot_token)) hex: %s", hashlib.sha256(bot_token.encode("utf-8")).hexdigest())
            logger.warning("computed_hmac: %s", hmac_hash)
            logger.warning("provided_hash: %s", provided_hash)
        except Exception:
            logger.exception("Failed while logging debug info for hash_mismatch")
        return False, "hash_mismatch"

    # optionally convert types (auth_date -> int)
    payload = dict(parsed)
    if "auth_date" in payload:
        try:
            payload["auth_date"] = int(payload["auth_date"])
        except Exception:
            pass

    logger.info("init_data verified successfully (variant used: %s) user_id=%s", used_variant, payload.get("id"))
    return True, payload