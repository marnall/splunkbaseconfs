"""Custom REST handler for the Test Connectivity button.

Accepts base_url and api_key via POST, calls CALL whisper.quota() to
validate connectivity and API key, and returns plan tier information.
"""

from __future__ import annotations

import time
from typing import Any

from whisper_api_client import WhisperAPIClient
from whisper_api_errors import WhisperAPIRequestError
from whisper_logging import get_logger, setup_logging

logger = get_logger("test_connectivity")
setup_logging("test_connectivity")


def _test_api_connectivity(base_url: str, api_key: str) -> dict[str, Any]:
    """Test API connectivity via CALL whisper.quota() and return plan tier.

    Uses WhisperAPIClient.quota() to validate both connectivity and the
    API key. The quota procedure returns the user's plan tier which
    differs based on the provided API key (Anonymous when no key).

    Args:
        base_url: Whisper API base URL.
        api_key: API key for authentication.

    Returns:
        Dictionary with success, plan, response_time_ms, and error.
    """
    result: dict[str, Any] = {
        "success": False,
        "plan": None,
        "response_time_ms": None,
        "error": None,
        "warning": None,
    }

    if not base_url:
        result["error"] = "Base URL is required"
        return result

    client = WhisperAPIClient(
        base_url=base_url,
        api_key=api_key or "",
        timeout=15,
        max_retries=0,
        rate_limit=0,
    )
    start = time.monotonic()

    try:
        quota_data = client.quota()
        result["success"] = True
        raw_plan = quota_data.get("plan", "Unknown")
        result["plan"] = raw_plan.title() if isinstance(raw_plan, str) else str(raw_plan)

        # Warn when an API key was provided but the plan is Anonymous
        if api_key and result["plan"].lower() == "anonymous":
            result["warning"] = (
                "API key not recognized — using Anonymous plan (2-hop depth limit). "
                "Verify your API key at console.whisper.security"
            )
    except WhisperAPIRequestError as exc:
        error = exc.error
        if error.status_code == 0:
            result["error"] = f"Connection failed to {base_url}"
        elif error.status_code == 408:
            result["error"] = "Request timed out after 15s"
        else:
            result["error"] = f"HTTP {error.status_code}: {error.message[:200]}"
        logger.warning("action=test_connectivity status=error error=%s", result["error"], exc_info=True)
    except Exception as exc:
        result["error"] = str(exc)
        logger.warning("action=test_connectivity status=error error=%s", result["error"], exc_info=True)
    finally:
        client.close()

    elapsed_ms = int((time.monotonic() - start) * 1000)
    result["response_time_ms"] = elapsed_ms

    return result


# Splunk admin handler — only loaded when running inside Splunk
try:
    import splunk.admin as admin

    class WhisperTestConnectivityHandler(admin.MConfigHandler):
        """REST handler for /whisper_test_connectivity endpoint."""

        def setup(self) -> None:
            """Declare supported arguments."""
            if self.requestedAction == admin.ACTION_CREATE:
                self.supportedArgs.addOptArg("base_url")
                self.supportedArgs.addOptArg("api_key")

        def handleCreate(self, confInfo) -> None:  # noqa: N802, N803 — Splunk SDK naming convention
            """Handle POST request to test connectivity.

            Args:
                confInfo: Splunk admin configuration info object used to
                    write response fields back to the caller.
            """
            base_url = self.callerArgs.data.get("base_url", [None])[0] or ""
            api_key = self.callerArgs.data.get("api_key", [None])[0] or ""

            result = _test_api_connectivity(base_url.rstrip("/"), api_key)

            # Write response fields into confInfo so they appear in the
            # REST response JSON under entry[].content
            stanza_id = self.callerArgs.id or "_test"
            for key, value in result.items():
                confInfo[stanza_id][key] = value

    if __name__ == "__main__":
        admin.init(WhisperTestConnectivityHandler, admin.CONTEXT_APP_AND_USER)

except ImportError:
    # Not running inside Splunk — handler class is unavailable
    pass
