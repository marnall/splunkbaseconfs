"""Bulletin board message utility for Whisper app health notifications.

Provides functions to post and clear persistent bulletin messages using
Splunk's ``services/messages`` REST API. Messages appear in the Splunk
Web banner area and are visible to users based on their roles.

Usage::

    from whisper_bulletin import post_message, clear_message

    # Post a warning when API is unreachable
    post_message(service, "whisper_api_down", "Whisper API is unreachable", "warn")

    # Clear the message when API recovers
    clear_message(service, "whisper_api_down")
"""

from __future__ import annotations

from typing import Any

from whisper_logging import get_logger

logger = get_logger("bulletin")

# Valid severity levels for Splunk messages
SEVERITY_LEVELS = ("info", "warn", "error")

# Prefix for all Whisper bulletin message names to avoid collisions
MESSAGE_PREFIX = "whisper_"

# Known message names used by Whisper components
MSG_API_DOWN = "whisper_api_connectivity_failed"
MSG_CONFIG_REQUIRED = "whisper_configuration_required"
MSG_RATE_LIMIT = "whisper_rate_limit_warning"
MSG_COLLECTION_ERROR = "whisper_collection_error"


def post_message(
    service: Any,
    name: str,
    value: str,
    severity: str = "warn",
) -> bool:
    """Post or update a bulletin message via Splunk services/messages REST API.

    If a message with the same name already exists, it will be replaced.
    Message names are automatically prefixed with ``whisper_`` if not
    already prefixed to avoid collisions with other apps.

    Args:
        service: Splunk SDK ``client.Service`` instance with an active session.
        name: Message identifier (e.g., ``"api_down"``). Will be prefixed
            with ``whisper_`` if not already.
        value: Human-readable message text displayed in the Splunk banner.
        severity: One of ``"info"``, ``"warn"``, or ``"error"``.

    Returns:
        True if the message was posted successfully, False otherwise.
    """
    if severity not in SEVERITY_LEVELS:
        logger.error(
            "action=post_message, status=error, reason=invalid_severity, severity=%s",
            severity,
        )
        return False

    if not name:
        logger.error("action=post_message, status=error, reason=empty_name")
        return False

    if not value:
        logger.error("action=post_message, status=error, reason=empty_value")
        return False

    # Ensure consistent prefix
    full_name = name if name.startswith(MESSAGE_PREFIX) else f"{MESSAGE_PREFIX}{name}"

    try:
        # Clear existing message first to avoid duplicates
        _delete_message(service, full_name)

        # Post new message via REST API
        service.post(
            "messages",
            name=full_name,
            value=value,
            severity=severity,
        )
        logger.info(
            "action=post_message, status=success, name=%s, severity=%s",
            full_name,
            severity,
        )
        return True

    except Exception as exc:
        logger.error(
            "action=post_message, status=error, name=%s, error=%s",
            full_name,
            exc,
        )
        return False


def clear_message(service: Any, name: str) -> bool:
    """Remove a bulletin message from the Splunk banner.

    Args:
        service: Splunk SDK ``client.Service`` instance with an active session.
        name: Message identifier to remove. Prefix ``whisper_`` is added
            automatically if not present.

    Returns:
        True if the message was cleared (or did not exist), False on error.
    """
    if not name:
        logger.error("action=clear_message, status=error, reason=empty_name")
        return False

    full_name = name if name.startswith(MESSAGE_PREFIX) else f"{MESSAGE_PREFIX}{name}"

    try:
        _delete_message(service, full_name)
        logger.info("action=clear_message, status=success, name=%s", full_name)
        return True
    except Exception as exc:
        logger.error(
            "action=clear_message, status=error, name=%s, error=%s",
            full_name,
            exc,
        )
        return False


def post_health_status(
    service: Any,
    api_status: str,
    error_message: str | None = None,
) -> None:
    """Post or clear health-related bulletin messages based on API status.

    Call this from the health input after each health check to keep the
    bulletin board in sync with current API state.

    Args:
        service: Splunk SDK ``client.Service`` instance.
        api_status: API health status string (e.g., ``"UP"``, ``"ERROR"``).
        error_message: Error detail when status is not ``"UP"``.
    """
    if api_status == "UP":
        # API is healthy: clear any existing down message
        clear_message(service, MSG_API_DOWN)
    else:
        # API is down or erroring: post a warning
        detail = f"Whisper API health check failed: {error_message}" if error_message else "Whisper API is unreachable"
        post_message(service, MSG_API_DOWN, detail, severity="warn")


def _delete_message(service: Any, name: str) -> None:
    """Delete a message by name, ignoring 404 errors.

    Args:
        service: Splunk SDK service instance.
        name: Full message name (with prefix).
    """
    import contextlib

    with contextlib.suppress(Exception):
        service.delete(f"messages/{name}")
