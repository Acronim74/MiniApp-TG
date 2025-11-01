"""
Utilities to verify Telegram WebApp initData per Telegram docs.

Algorithm summary:
- init_data is a query-string-like string: key1=value1&key2=value2&...&hash=xxxxx
- Remove hash param, build a data_check_string by joining sorted keys as "key=value\nkey2=value2..."
- Compute secret_key = SHA256(bot_token)
- Compute HMAC_SHA256(secret_key, data_check_string).hexdigest()
- Compare hex digest to provided hash
"""
from typing import Tuple, Dict, Any
import hashlib
import hmac
import urllib.parse
import logging

logger = logging.getLogger("app.telegram_auth")


def parse_init_data(init_data: str) -> Dict[str, str]:
    # parse like query string
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    return parsed


def verify_init_data(init_data: str, bot_token: str) -> Tuple[bool, Dict[str, Any] | str]:
    """
    Returns (True, payload_dict_without_hash) if verification succeeded,
    otherwise (False, error_message).
    """
    try:
        parsed = parse_init_data(init_data)
    except Exception as e:
        return False, f"parse_error: {e}"

    provided_hash = parsed.pop("hash", None)
    if not provided_hash:
        return False, "no hash in init_data"

    # build data_check_string
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
            logger.warning("init_data verification failed: hash_mismatch")
            logger.debug("init_data (raw): %s", init_data)
            logger.debug("parsed fields: %s", parsed)
            logger.debug("data_check_string: %s", data_check_string)
            logger.debug("secret_key (SHA256(bot_token)) hex: %s", hashlib.sha256(bot_token.encode("utf-8")).hexdigest())
            logger.debug("computed_hmac: %s", hmac_hash)
            logger.debug("provided_hash: %s", provided_hash)
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

    return True, payload