"""
Utilities to verify Telegram WebApp initData per Telegram docs.

This implementation is tolerant to a few common variants:
- init_data = "query_id=...&user=...&hash=..."
- init_data = "tgWebAppData=query_id%3D...%26user%3D...%26hash%3D..." (wrapper)
- init_data = "query_id%3D...%26user%3D...%26hash%3D..." (raw percent-encoded fragment)

We attempt verification on several normalized forms until one succeeds.
Additionally, when HMAC mismatches we try a set of safe normalizations limited to the "user"
value (replace '\/'->'/', parse JSON and re-dump without escaping slashes, etc.) to cover
common encoding/serialization differences.
"""
from typing import Tuple, Dict, Any
import hashlib
import hmac
import urllib.parse
import json
import logging

logger = logging.getLogger("app.telegram_auth")


def parse_init_data(init_data: str) -> Dict[str, str]:
    # parse like query string
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    return parsed


def _try_parse_variants(init_data: str) -> Tuple[Dict[str, str], str, str]:
    """
    Try different normalization variants and return (parsed_dict, variant_name, normalized_init_data)
    variant_name is one of: "raw", "tgWebAppData_inner", "unquote_once", "unquote_twice"
    normalized_init_data is the string corresponding to parsed dict (useful for logging)
    """
    # 1) try raw
    parsed = parse_init_data(init_data)
    if "hash" in parsed:
        return parsed, "raw", init_data

    # 2) if top-level has tgWebAppData key (like tgWebAppData=percent-encoded...), decode inner
    if "tgWebAppData" in parsed:
        try:
            inner = urllib.parse.unquote(parsed["tgWebAppData"])
            parsed_inner = parse_init_data(inner)
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

    # 3) try unquote once if looks percent-encoded
    low = init_data.lower()
    if "%3d" in low or "%26" in low or "%7b" in low:
        try:
            un1 = urllib.parse.unquote(init_data)
            parsed_un1 = parse_init_data(un1)
            if "hash" in parsed_un1:
                return parsed_un1, "unquote_once", un1
            parsed = parsed_un1
            variant = "unquote_once"
            norm = un1
        except Exception:
            pass

    # 4) try unquote twice
    try:
        un2 = urllib.parse.unquote(urllib.parse.unquote(init_data))
        parsed_un2 = parse_init_data(un2)
        if "hash" in parsed_un2:
            return parsed_un2, "unquote_twice", un2
        parsed = parsed_un2
        variant = "unquote_twice"
        norm = un2
    except Exception:
        pass

    return parsed, variant, norm


def _build_data_check_string_from_parsed(parsed: Dict[str, str]) -> str:
    items = []
    for k in sorted(parsed.keys()):
        items.append(f"{k}={parsed[k]}")
    return "\n".join(items)


def _compute_hmac_hex(bot_token: str, data_check_string: str) -> str:
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    return hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()


def _try_user_normalizations_and_verify(parsed: Dict[str, str], provided_hash: str, bot_token: str) -> Tuple[bool, Dict[str, str], str]:
    """
    Try safe normalizations limited to the 'user' value and recompute HMAC.
    Returns (True, corrected_parsed, variant_name) if a normalization yields a matching HMAC.
    Otherwise returns (False, parsed, last_variant_tried).
    """
    user_val = parsed.get("user")
    if user_val is None:
        return False, parsed, "no_user"

    variants = []

    # original user (already tried previously, but include for completeness)
    variants.append(("original_user", user_val))

    # 1) replace escaped slashes '\/' -> '/'
    variants.append(("replace_escaped_slashes", user_val.replace("\\/", "/")))

    # 2) try parsing JSON after replacing '\/'->'/' and re-dump compact without escaping slashes
    try:
        candidate = user_val.replace("\\/", "/")
        obj = json.loads(candidate)
        dumped = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
        variants.append(("user_json_parsed_and_dumped", dumped))
    except Exception:
        # parsing may fail if representation is not valid JSON in that exact form
        pass

    # 3) try removing backslashes before quotes (some serializers escape quotes differently)
    variants.append(("remove_backslash_before_quote", user_val.replace('\\"', '"')))

    # 4) try replacing escaped backslashes '\\\\' -> '\\' (double-escaped)
    variants.append(("unescape_double_backslashes", user_val.replace("\\\\", "\\")))

    # Deduplicate preserving order
    seen = set()
    uniq = []
    for name, v in variants:
        if v is None:
            continue
        if v in seen:
            continue
        seen.add(v)
        uniq.append((name, v))

    # Try each candidate by reconstructing parsed dict and computing HMAC
    for name, user_candidate in uniq:
        candidate_parsed = dict(parsed)
        candidate_parsed["user"] = user_candidate
        dcs = _build_data_check_string_from_parsed(candidate_parsed)
        h = _compute_hmac_hex(bot_token, dcs)
        if h == provided_hash:
            return True, candidate_parsed, f"user_norm:{name}"

    # no match
    return False, parsed, "user_norm_none"


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
            logger.warning("init_data (raw/normalized): %s", normalized_init)
            logger.warning("parsed keys: %s", list(parsed.keys()))
        except Exception:
            logger.exception("Failed while logging debug info for missing hash")
        return False, "no hash in init_data"

    # Build canonical data_check_string and compute HMAC
    data_check_string = _build_data_check_string_from_parsed(parsed)
    computed_hmac = _compute_hmac_hex(bot_token, data_check_string)

    if hmac.compare_digest(computed_hmac, provided_hash):
        # success on first try
        payload = dict(parsed)
        if "auth_date" in payload:
            try:
                payload["auth_date"] = int(payload["auth_date"])
            except Exception:
                pass
        logger.info("init_data verified successfully (variant used: %s) user_id=%s", used_variant, payload.get("id"))
        return True, payload

    # If HMAC mismatched, try user normalizations (safe, limited scope)
    ok, corrected_parsed, user_norm_variant = _try_user_normalizations_and_verify(parsed, provided_hash, bot_token)
    if ok:
        payload = dict(corrected_parsed)
        if "auth_date" in payload:
            try:
                payload["auth_date"] = int(payload["auth_date"])
            except Exception:
                pass
        logger.info("init_data verified successfully after user normalization (%s)", user_norm_variant)
        return True, payload

    # Nothing matched — log details for diagnosis
    try:
        logger.warning("init_data verification failed: hash_mismatch (variant tried: %s)", used_variant)
        logger.warning("init_data (raw/normalized): %s", normalized_init)
        logger.warning("parsed fields: %s", parsed)
        logger.warning("data_check_string: %s", data_check_string)
        logger.warning("secret_key (SHA256(bot_token)) hex: %s", hashlib.sha256(bot_token.encode("utf-8")).hexdigest())
        logger.warning("computed_hmac: %s", computed_hmac)
        logger.warning("provided_hash: %s", provided_hash)
    except Exception:
        logger.exception("Failed while logging debug info for hash_mismatch")
    return False, "hash_mismatch"