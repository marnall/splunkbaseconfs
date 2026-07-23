#!/usr/bin/env python3
"""
DarkStrata Get Alert Details - Adaptive Response Action (Enrichment)

Retrieves full details of a credential exposure alert from DarkStrata
for enrichment purposes in Splunk ES.

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


class GetAlertDetailsAction(DarkStrataActionBase):
    """Get full details of a DarkStrata alert for enrichment."""

    ACTION_NAME = "darkstrata_get_alert_details"

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the get alert details action."""
        # Validate required parameters
        account_name = params.get("account")
        alert_id = params.get("alert_id")

        if not account_name:
            raise DarkStrataActionError("Account name is required")
        if not alert_id:
            raise DarkStrataActionError("Alert ID is required")

        self.logger.info("Getting details for alert %s using account %s", alert_id, account_name)

        # Get account configuration
        account_config = self.get_account_config(account_name)

        # Make API call to get alert details
        endpoint = f"/alerts/{alert_id}"
        result = self.make_api_request(account_config, "GET", endpoint)

        self.logger.info("Successfully retrieved details for alert %s", alert_id)

        # Format the response for enrichment
        return {
            "alert_id": result.get("id", alert_id),
            "status": result.get("status"),
            "severity": result.get("severity"),
            "title": result.get("title"),
            "description": result.get("description"),
            "created_at": result.get("created_at"),
            "updated_at": result.get("updated_at"),
            "acknowledged_at": result.get("acknowledged_at"),
            "closed_at": result.get("closed_at"),
            "exposed_credentials_count": result.get("exposed_credentials_count", 0),
            "affected_domains": result.get("affected_domains", []),
            "source_type": result.get("source_type"),
            "source_name": result.get("source_name"),
            "threat_actor": result.get("threat_actor"),
            "malware_family": result.get("malware_family"),
            "first_seen": result.get("first_seen"),
            "last_seen": result.get("last_seen"),
            # User info
            "acknowledged_by": result.get("acknowledged_by_user", {}).get("email"),
            "closed_by": result.get("closed_by_user", {}).get("email"),
        }


def main() -> None:
    """Main entry point for the alert action."""
    # Set up logging
    if log is not None:
        log.Logs.set_context()
        logger = log.Logs().get_logger(GetAlertDetailsAction.ACTION_NAME)
    else:
        import logging

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(GetAlertDetailsAction.ACTION_NAME)

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
    action = GetAlertDetailsAction(session_key=session_key, logger=logger)
    result = action.run(payload)

    # Write result
    write_result(result)

    # Exit with appropriate code
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
