"""Shared Splunk time-token validation used by both alerts/params.py and
health/metrics_service.py — anything that reaches SPL as a bare (unquoted)
token, such as earliest/latest time bounds, must be constrained to this
allowlist rather than interpolated raw."""

import re

SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_:@+./-]+$")
EPOCH_RE = re.compile(r"^\d+(\.\d+)?$")


class TimeTokenError(ValueError):
    """Raised for an unsafe or missing time-bound token."""


def validate_time_token(value, field_name: str) -> str:
    token = str(value or "").strip()
    if not token or not SAFE_TOKEN_RE.match(token):
        raise TimeTokenError(f"Invalid {field_name}: {value}")
    return token
