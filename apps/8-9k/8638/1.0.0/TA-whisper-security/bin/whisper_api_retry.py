"""Retry logic and error parsing for the Whisper API client.

Provides exponential backoff with jitter and structured error parsing
for HTTP responses. Extracted from whisper_api_client.py to keep
module size under the 500-line maintainability limit.
"""

from __future__ import annotations

import contextlib
import random
from typing import TYPE_CHECKING, Any

from whisper_api_errors import WhisperAPIError
from whisper_logging import get_logger

if TYPE_CHECKING:
    import requests

logger = get_logger("api_retry")

# Backoff defaults
DEFAULT_BACKOFF_BASE = 1.0
DEFAULT_BACKOFF_MAX = 30.0


def parse_error(response: requests.Response) -> WhisperAPIError:
    """Parse an error response into a structured error object.

    Supports RFC 7807 Problem Detail format (type/title/status/detail)
    with fallback to legacy format (message/error) for backward
    compatibility.

    Args:
        response: The HTTP response with non-2xx status.

    Returns:
        Structured error with retry classification.
    """
    status = response.status_code
    body: dict[str, Any] = {}
    extra: dict[str, Any] = {}

    with contextlib.suppress(ValueError):
        body = response.json()

    # Extract message: RFC 7807 (detail > title) then legacy (message > error)
    message = str(body.get("detail", body.get("title", body.get("message", body.get("error", response.text)))))

    # Extract error_type from RFC 7807 'type' URI (e.g. ".../query-depth-exceeded" -> "query-depth-exceeded")
    rfc7807_type = body.get("type", "")
    rfc7807_error_type = ""
    if rfc7807_type and "/" in rfc7807_type:
        rfc7807_error_type = rfc7807_type.rsplit("/", 1)[-1]

    # Collect additional RFC 7807 fields into extra
    _rfc7807_standard_keys = {"type", "title", "status", "detail", "instance"}
    for key, value in body.items():
        if key not in _rfc7807_standard_keys and key not in ("message", "error"):
            extra[key] = value

    if status == 400:
        error_type = "CypherParseException"
        # Detect query-depth-exceeded errors from RFC 7807 type or message content
        msg_lower = message.lower()
        if rfc7807_error_type == "query-depth-exceeded" or "depth" in msg_lower or "hop" in msg_lower:
            error_type = "QueryDepthExceeded"
            message = (
                f"{message}. "
                "Your API plan limits query traversal depth. "
                "Anonymous=2 hops, Free=3 hops, Professional=5 hops. "
                "Upgrade your plan or reduce query depth."
            )
            logger.warning(
                "action=query status=depth_exceeded message=%s",
                message,
            )
        return WhisperAPIError(
            status_code=400,
            error_type=error_type,
            message=message,
            retryable=False,
            raw_response=response.text,
            extra=extra or None,
        )
    elif status == 401:
        return WhisperAPIError(
            status_code=401,
            error_type="Unauthorized",
            message="Invalid or missing API key",
            retryable=False,
        )
    elif status == 408:
        return WhisperAPIError(
            status_code=408,
            error_type="QueryTimeout",
            message=message,
            retryable=False,
            raw_response=response.text,
            extra=extra or None,
        )
    elif status == 429:
        return WhisperAPIError(
            status_code=429,
            error_type="RateLimited",
            message="Rate limit exceeded",
            retryable=True,
        )
    elif status == 503:
        return WhisperAPIError(
            status_code=503,
            error_type="ExternalApiUnavailable",
            message=message,
            retryable=True,
        )
    elif status == 504:
        return WhisperAPIError(
            status_code=504,
            error_type="GatewayTimeout",
            message=message,
            retryable=True,
            raw_response=response.text,
            extra=extra or None,
        )
    elif status >= 500:
        return WhisperAPIError(
            status_code=status,
            error_type="ServerError",
            message=message,
            retryable=True,
        )
    else:
        return WhisperAPIError(
            status_code=status,
            error_type="UnexpectedError",
            message=message,
            retryable=False,
            raw_response=response.text,
        )


def calculate_backoff(
    attempt: int,
    response: requests.Response | None = None,
) -> float:
    """Calculate backoff delay with exponential growth and jitter.

    Respects the Retry-After header if present.

    Args:
        attempt: Zero-based retry attempt number.
        response: Optional response to check for Retry-After header.

    Returns:
        Delay in seconds before next retry.
    """
    # Check Retry-After header
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass

    # Exponential backoff with full jitter
    delay = DEFAULT_BACKOFF_BASE * (2**attempt)
    delay = min(delay, DEFAULT_BACKOFF_MAX)
    return random.uniform(0, delay)  # noqa: S311
