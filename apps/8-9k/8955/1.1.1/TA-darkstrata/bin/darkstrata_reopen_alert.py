#!/usr/bin/env python3
"""
DarkStrata Reopen Alert - Adaptive Response Action

Reopens a previously closed credential exposure alert in DarkStrata,
moving it back to "Active" status for further investigation.

Usage:
    This script is invoked by Splunk as an alert action. It receives a JSON
    payload via stdin when called with --execute flag.
"""

from __future__ import annotations

import sys
from typing import Any

# UCC-generated imports
try:
    import import_declare_test  # noqa: F401
    from solnlib import log
except ImportError:
    log = None

from darkstrata_action_base import (
    DarkStrataActionBase,
    DarkStrataActionError,
    parse_payload,
    write_result,
)


class ReopenAlertAction(DarkStrataActionBase):
    """Reopen a previously closed DarkStrata alert."""

    ACTION_NAME = "darkstrata_reopen_alert"

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the reopen alert action."""
        # Validate required parameters
        account_name = params.get("account")
        alert_id = params.get("alert_id")

        if not account_name:
            raise DarkStrataActionError("Account name is required")
        if not alert_id:
            raise DarkStrataActionError("Alert ID is required")

        self.logger.info("Reopening alert %s using account %s", alert_id, account_name)

        # Get account configuration
        account_config = self.get_account_config(account_name)

        # Make API call to reopen the alert (set status to ACTIVE)
        endpoint = f"/alerts/{alert_id}"
        result = self.make_api_request(account_config, "PATCH", endpoint, data={"status": "ACTIVE"})

        self.logger.info(
            "Successfully reopened alert %s, new status: %s",
            alert_id,
            result.get("status"),
        )

        return {
            "alert_id": result.get("id", alert_id),
            "status": result.get("status"),
            "updated_at": result.get("updated_at"),
        }


def main() -> None:
    """Main entry point for the alert action."""
    # Set up logging
    if log is not None:
        log.Logs.set_context()
        logger = log.Logs().get_logger(ReopenAlertAction.ACTION_NAME)
    else:
        import logging

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(ReopenAlertAction.ACTION_NAME)

    # Parse payload
    payload = parse_payload()

    if not payload:
        write_result(
            {
                "success": False,
                "message": "No payload received. This action must be invoked by Splunk.",
            }
        )
        sys.exit(1)

    # Get session key from payload
    session_key = payload.get("session_key", "")

    # Create and run action
    action = ReopenAlertAction(session_key=session_key, logger=logger)
    result = action.run(payload)

    # Write result
    write_result(result)

    # Exit with appropriate code
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
