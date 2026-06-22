"""Alert action script for Whisper Security enrichment.

This is the entry point for the ``whisper_enrich`` alert action defined in
``alert_actions.conf``.  When triggered by a Splunk alert, it reads the
payload from the file path passed as a CLI argument, enriches the event via
the Whisper Knowledge Graph API, and logs the results.
"""

from __future__ import annotations

import gzip
import json
import os
import sys

# Adjust path so sibling modules are importable
sys.path.insert(0, os.path.dirname(__file__))

import splunklib.client as splunk_client  # noqa: E402
from whisper_adaptive_response import run_adaptive_response  # noqa: E402
from whisper_api_client import WhisperAPIClient  # noqa: E402
from whisper_config import get_config  # noqa: E402
from whisper_logging import get_logger, setup_logging  # noqa: E402

logger = get_logger("enrich")


def run(payload: dict) -> int:
    """Execute the alert action.

    Args:
        payload: The alert action payload from Splunk containing
            ``configuration``, ``result``, and ``session_key``.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    try:
        result = payload.get("result", {})
        session_key = payload.get("session_key", "")

        if not session_key:
            logger.error("action=enrich_alert, status=error, reason=missing_session_key")
            return 1

        service = splunk_client.connect(token=session_key, app="TA-whisper-security")
        config = get_config(service)

        if not config.api_key:
            logger.error("action=enrich_alert, status=error, reason=missing_api_key")
            return 1

        client = WhisperAPIClient(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
            proxy=config.proxy_url,
        )

        try:
            enrichment_results = run_adaptive_response(client, result)
            logger.info(
                "Enriched %d indicators from alert action",
                len(enrichment_results),
            )
            return 0
        finally:
            client.close()

    except Exception:
        logger.exception("action=enrich_alert, status=error")
        return 1


def main() -> None:
    """Entry point when invoked by Splunk alert action framework."""
    setup_logging("enrich")

    if len(sys.argv) < 2:
        logger.error("action=enrich_alert, status=error, reason=missing_payload_arg")
        sys.exit(1)

    payload_file = sys.argv[1]
    try:
        if payload_file.endswith(".gz"):
            with gzip.open(payload_file, "rt") as f:
                payload = json.load(f)
        else:
            with open(payload_file) as f:
                payload = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.exception("action=enrich_alert, status=error, reason=payload_read_failed, file=%s", payload_file)
        sys.exit(1)

    exit_code = run(payload)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
