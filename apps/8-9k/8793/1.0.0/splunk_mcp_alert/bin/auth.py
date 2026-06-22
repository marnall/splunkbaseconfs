"""Bearer token authentication against Splunk's auth endpoint."""

import logging
from typing import Optional, Tuple

from splunk_api import SplunkAPIClient

logger = logging.getLogger(__name__)

REQUIRED_CAPABILITY = "mcp_alert_execute"


def validate_bearer_token(
    token: str,
    system_authtoken: str,
    base_url: str,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate a Bearer token against Splunk's authentication endpoint.

    Args:
        token: The Bearer token from the Authorization header.
        system_authtoken: Splunk system auth token for API access.
        base_url: Splunk management base URL.

    Returns:
        Tuple of (is_valid, username_or_none, error_message_or_none).
    """
    if not token or not token.strip():
        return False, None, "Missing or empty Bearer token"

    try:
        client = SplunkAPIClient(base_url=base_url, token=token)
        result = client.call_api("GET", "/services/authentication/current-context")

        entry = result.get("entry", [])
        if not entry:
            return False, None, "No authentication context returned"

        content = entry[0].get("content", {})
        username = content.get("username")
        roles = content.get("roles", [])
        capabilities = content.get("capabilities", [])

        if not username:
            return False, None, "No username in authentication context"

        if REQUIRED_CAPABILITY not in capabilities:
            return (
                False,
                username,
                f"User '{username}' lacks required capability: {REQUIRED_CAPABILITY}",
            )

        logger.info("Authenticated user '%s' with roles %s", username, roles)
        return True, username, None

    except Exception as e:
        logger.warning("Token validation failed: %s", e)
        return False, None, f"Authentication failed: {e}"
