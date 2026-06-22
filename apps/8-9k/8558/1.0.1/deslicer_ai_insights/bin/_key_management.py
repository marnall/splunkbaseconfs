# API key rotation and server-status checking.
# Imported by _enrollment.py and deslicer_ai_insights_helper.py.

import json
import logging
import os
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Optional

KEY_EXPIRY_WARNING_DAYS = 7

_REDACTED = "[REDACTED]"
_BEARER_PATTERN = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-+/=]+")

# JSON-style `"<key>": "<value>"` fields whose value is always credential
# material. Match keys case-insensitively and tolerate surrounding whitespace.
# We deliberately match shape rather than parse, so we still redact when the
# surrounding payload is invalid JSON (which is exactly the path that surfaces
# new rotated keys via JSONDecodeError).
_SENSITIVE_JSON_FIELDS = (
    "api_key",
    "api_token",
    "access_token",
    "refresh_token",
    "secret",
    "password",
    "token",
    "new_key",
    "key",
)
_JSON_FIELD_PATTERN = re.compile(
    r'(?i)("(?:' + "|".join(_SENSITIVE_JSON_FIELDS) + r')"\s*:\s*")[^"]*(")'
)


def _scrub_secrets(text: str, *secrets: str) -> str:
    """Best-effort redaction of credential material from log strings.

    Redacts:
    - Any literal occurrence of the supplied secret values (e.g. the
      *current* api_key passed in by the caller).
    - `Bearer <token>` Authorization headers.
    - JSON-style `"<sensitive-field>": "<value>"` pairs (api_key,
      token, secret, etc.) -- catches *new* rotated credentials in
      partial / malformed JSON before they reach Splunk's index.

    Used before logging text we don't fully control (e.g. subprocess
    stderr / stdout from the rotation binary).
    """
    if not text:
        return text
    cleaned = text
    for secret in secrets:
        if secret and len(secret) >= 4:
            cleaned = cleaned.replace(secret, _REDACTED)
    cleaned = _BEARER_PATTERN.sub(r"\1" + _REDACTED, cleaned)
    cleaned = _JSON_FIELD_PATTERN.sub(r"\1" + _REDACTED + r"\2", cleaned)
    return cleaned


def key_needs_rotation(creds: dict, logger: logging.Logger) -> bool:
    expires_at = creds.get("api_key_expires_at", "")
    if not expires_at:
        return False
    try:
        ts = expires_at.replace("Z", "+00:00")
        # Python < 3.11 only supports up to 6 fractional digits (microseconds).
        # Rust/Go timestamps may include 9 digits (nanoseconds) — truncate.
        ts = re.sub(r"(\.\d{6})\d+", r"\1", ts)
        expiry = datetime.fromisoformat(ts)
        now = datetime.now(tz=timezone.utc)
        days = (expiry - now).days
        if days < 0:
            logger.warning("API key has expired (%s) — re-enrolling", expires_at)
            return True
        if days <= KEY_EXPIRY_WARNING_DAYS:
            logger.warning("API key expires in %d day(s) — rotating", days)
            return True
        return False
    except Exception:
        logger.debug("Could not parse expiry '%s'", expires_at, exc_info=True)
        return False


def check_server_key_status(
    creds: dict,
    logger: logging.Logger,
) -> Optional[str]:
    """Poll GET /api/v1/key-status. Returns 'rotate', 'revoked', or None."""
    api_url = creds.get("observer_api_url", "")
    api_key = creds.get("api_token", "")
    if not api_url or not api_key:
        return None

    url = f"{api_url.rstrip('/')}/api/v1/key-status"
    req = urllib.request.Request(  # noqa: S310
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode())
            if data.get("needs_rotation"):
                server_expiry = data.get("expires_at", "")
                logger.info(
                    "Server signaled rotation (expires %s)", server_expiry or "?"
                )
                if server_expiry:
                    creds["api_key_expires_at"] = server_expiry
                return "rotate"
            if not data.get("is_active"):
                logger.warning("Server reports key is revoked/inactive")
                return "revoked"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            logger.warning("Key-status: 401 (key revoked or expired)")
            return "revoked"
        logger.debug("Key-status HTTP %d", e.code)
    except Exception as exc:
        logger.debug("Key-status check failed: %s", exc)
    return None


def run_key_rotation(
    session_key: str,
    creds: dict,
    binary: str,
    logger: logging.Logger,
    write_fn,
) -> Optional[dict]:
    """Invoke binary --rotate-key and update credentials in store."""
    api_url = creds.get("observer_api_url", "")
    api_key = creds.get("api_token", "")
    if not api_url:
        logger.warning("Cannot rotate key: observer_api_url is missing")
        return None
    if not api_key:
        logger.warning("Cannot rotate key: no current API key")
        return None

    cmd = [binary, "--rotate-key", "--api-url", api_url]
    child_env = os.environ.copy()
    child_env["NO_COLOR"] = "1"
    child_env["API_KEY"] = api_key

    logger.info("Starting key rotation")
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            env=child_env,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Key rotation timed out after 60s")
        return None
    except OSError as e:
        logger.warning("Key rotation binary execution failed: %s", e)
        return None

    if result.returncode != 0:
        # SECURITY: stderr from the rotation binary is untrusted and may
        # echo back the API key, a Bearer header, or other credential
        # material. Scrub before logging so nothing secret reaches Splunk.
        stderr_raw = result.stderr.strip() if result.stderr else ""
        stderr_safe = (
            _scrub_secrets(stderr_raw, api_key) if stderr_raw else "no stderr"
        )
        logger.warning(
            "Key rotation failed (exit %d): %s",
            result.returncode,
            stderr_safe,
        )
        return None

    stdout = result.stdout.strip()
    if not stdout:
        logger.warning("Key rotation returned empty response")
        return None

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        # SECURITY: invalid JSON might still contain a partial credential
        # echoed back from the binary; scrub before logging.
        logger.warning(
            "Key rotation returned invalid JSON: %s",
            _scrub_secrets(stdout[:200], api_key),
        )
        return None

    new_key = data.get("api_key", "")
    new_tenant = data.get("tenant_id", "") or creds.get("tenant_id", "")
    new_expires_at = data.get("api_key_expires_at", "")

    if not new_key:
        logger.warning("Key rotation response missing api_key")
        return None

    try:
        write_fn(
            session_key,
            "enrolled_account",
            new_key,
            new_tenant,
            api_url,
            logger,
            expires_at=new_expires_at,
        )
    except Exception:
        logger.exception("Failed to persist rotated key")
        return None

    # SECURITY: never log any portion of the rotated key (not even a
    # prefix); log only status/expiry to keep credentials out of Splunk.
    logger.info(
        "Key rotation successful: expires=%s",
        new_expires_at or "never",
    )
    return {
        "api_token": new_key,
        "tenant_id": new_tenant,
        "observer_api_url": api_url,
        "api_key_expires_at": new_expires_at,
    }
