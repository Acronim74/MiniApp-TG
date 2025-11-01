"""
Utilities to verify Telegram WebApp initData per Telegram docs.

Robust verifier:
- tries raw / tgWebAppData inner / unquote once / unquote twice
- builds data_check_string and validates HMAC (SHA256(bot_token) -> HMAC-SHA256)
- on HMAC mismatch, attempts safe normalizations limited to the 'user' value
  (replace '\/'->'/', parse+dump JSON without escaping slashes, remove backslash-before-quote, etc.)
- on success: converts 'user' JSON string into a dict (if possible), returns structured payload
"""
from typing import Tuple, Dict, Any
import hashlib
import hmac
import urllib.parse
import json
import logging

logger = logging.getLogger("app.telegram_auth")


def _parse_qs(init_data: str) -> Dict[str, str]:
    return dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))


def _build_data_check_string(parsed: Dict[str, str]) -> str:
    items = []
    for k in sorted(parsed.keys()):
        items.append(f"{k}={parsed[k]}")
    return "\n".join(items)


def _compute_hmac_hex(bot_token: str, data_check_string: str) -> str:
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    return hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()


def _try_parse_variants(init_data: str) -> Tuple[Dict[str, str], str, str]:
    parsed = _parse_qs(init_data)
    if "hash" in parsed:
        return parsed, "raw", init_data

    # tgWebAppData wrapper
    if "tgWebAppData" in parsed:
        try:
            inner = urllib.parse.unquote(parsed["tgWebAppData"])
            parsed_inner = _parse_qs(inner)
            if "hash" in parsed_inner:
                return parsed_inner, "tgWebAppData_inner", inner
            parsed = parsed_inner
            variant = "tgWebAppData_inner"
            norm = inner
        except Exception:
            variant = "tgWebAppData_inner_failed"
            norm = init_data
    else:
        variant = "raw"
        norm = init_data

    low = init_data.lower()
    if "%3d" in low or "%26" in low or "%7b" in low:
        try:
            un1 = urllib.parse.unquote(init_data)
            p_un1 = _parse_qs(un1)
            if "hash" in p_un1:
                return p_un1, "unquote_once", un1
            parsed = p_un1
            variant = "unquote_once"
            norm = un1
        except Exception:
            pass

    try:
        un2 = urllib.parse.unquote(urllib.parse.unquote(init_data))
        p_un2 = _parse_qs(un2)
        if "hash" in p_un2:
            return p_un2, "unquote_twice", un2
        parsed = p_un2
        variant = "unquote_twice"
        norm = un2
    except Exception:
        pass

    return parsed, variant, norm


def _try_user_normalizations_and_verify(parsed: Dict[str, str], provided_hash: str, bot_token: str) -> Tuple[bool, Dict[str, str], str]:
    user_val = parsed.get("user")
    if user_val is None:
        return False, parsed, "no_user"

    variants = []
    variants.append(("original_user", user_val))
    variants.append(("replace_escaped_slashes", user_val.replace("\\/", "/")))

    try:
        candidate = user_val.replace("\\/", "/")
        obj = json.loads(candidate)
        dumped = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        variants.append(("user_json_parsed_and_dumped", dumped))
    except Exception:
        pass

    variants.append(("remove_backslash_before_quote", user_val.replace('\\"', '"')))
    variants.append(("unescape_double_backslashes", user_val.replace("\\\\", "\\")))

    seen = set()
    uniq = []
    for name, v in variants:
        if v is None:
            continue
        if v in seen:
            continue
        seen.add(v)
        uniq.append((name, v))

    for name, user_candidate in uniq:
        candidate_parsed = dict(parsed)
        candidate_parsed["user"] = user_candidate
        dcs = _build_data_check_string(candidate_parsed)
        h = _compute_hmac_hex(bot_token, dcs)
        if h == provided_hash:
            return True, candidate_parsed, f"user_norm:{name}"

    return False, parsed, "user_norm_none"


def _try_parse_user_field_to_obj(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    If payload contains a 'user' string, try to parse it into a dict.
    Replaces '\/' -> '/' before json.loads to handle escaped slashes.
    Returns modified payload (may be the same if parsing fails).
    """
    user_raw = payload.get("user")
    if isinstance(user_raw, str):
        try:
            candidate = user_raw.replace("\\/", "/")
            obj = json.loads(candidate)
            payload["user"] = obj
        except Exception:
            # leave as-is if parsing fails
            pass
    return payload


def verify_init_data(init_data: str, bot_token: str) -> Tuple[bool, Dict[str, Any] | str]:
    """
    Returns (True, payload_dict_without_hash) if verification succeeded,
    otherwise (False, error_message).
    """
    if not isinstance(init_data, str):
        return False, "init_data not a string"

    parsed, used_variant, normalized_init = _try_parse_variants(init_data)

    provided_hash = parsed.pop("hash", None)
    if not provided_hash:
        try:
            logger.warning("init_data verification failed: no hash in init_data (variant tried: %s)", used_variant)
            logger.debug("init_data (raw/normalized): %s", normalized_init)
            logger.debug("parsed keys: %s", list(parsed.keys()))
        except Exception:
            logger.exception("Failed while logging debug info for missing hash")
        return False, "no hash in init_data"

    data_check_string = _build_data_check_string(parsed)
    computed_hmac = _compute_hmac_hex(bot_token, data_check_string)

    if hmac.compare_digest(computed_hmac, provided_hash):
        payload = dict(parsed)
        payload = _try_parse_user_field_to_obj(payload)
        if "auth_date" in payload:
            try:
                payload["auth_date"] = int(payload["auth_date"])
            except Exception:
                pass
        # extract user id for logging if possible
        user_id = None
        if isinstance(payload.get("user"), dict):
            user_id = payload["user"].get("id")
        logger.info("init_data verified successfully (variant used: %s) user_id=%s", used_variant, user_id)
        return True, payload

    # Try safe user normalizations
    ok, corrected_parsed, user_norm_variant = _try_user_normalizations_and_verify(parsed, provided_hash, bot_token)
    if ok:
        payload = dict(corrected_parsed)
        payload = _try_parse_user_field_to_obj(payload)
        if "auth_date" in payload:
            try:
                payload["auth_date"] = int(payload["auth_date"])
            except Exception:
                pass
        user_id = None
        if isinstance(payload.get("user"), dict):
            user_id = payload["user"].get("id")
        logger.info("init_data verified successfully after user normalization (%s) user_id=%s", user_norm_variant, user_id)
        return True, payload

    # Nothing matched — log details for diagnosis (avoid printing full secret)
    try:
        logger.warning("init_data verification failed: hash_mismatch (variant tried: %s)", used_variant)
        logger.debug("init_data (raw/normalized): %s", normalized_init)
        logger.debug("parsed fields: %s", parsed)
        logger.debug("data_check_string: %s", data_check_string)
        # Do NOT log full secret_key in production; log only prefix if strictly needed
        try:
            secret_hex = hashlib.sha256(bot_token.encode("utf-8")).hexdigest()
            logger.debug("secret_key (sha256 hex prefix): %s", secret_hex[:8])
        except Exception:
            pass
        logger.debug("computed_hmac: %s", computed_hmac)
        logger.debug("provided_hash: %s", provided_hash)
    except Exception:
        logger.exception("Failed while logging debug info for hash_mismatch")
    return False, "hash_mismatch"