#!/usr/bin/env python3
"""
Custom alert action to update Cyberint Argos alert status.

Triggered via sendalert SPL command or scheduled alert action.
Reads search results from the results_file, extracts ref_id values,
and calls the Cyberint API to update their status.
"""
import csv
import gzip
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import import_declare_test  # noqa: E402, F401
import utils  # noqa: E402
from argos_client import CyberintClient  # noqa: E402

VALID_STATUSES = {"open", "acknowledged", "closed"}
VALID_CLOSURE_REASONS = {
    "resolved",
    "irrelevant",
    "false_positive",
    "irrelevant_alert_subtype",
    "no_longer_a_threat",
    "other",
}
MAX_BATCH_SIZE = 100


def run(payload):
    """Execute the alert action with the given payload dict."""
    config = payload.get("configuration", {})
    session_key = payload.get("session_key")
    results_file = payload.get("results_file")

    # Required parameters
    account = config.get("account", "")
    instance_domain = config.get("instance_domain", "")
    client_name = config.get("client_name", "")
    status = config.get("status", "")

    # Optional parameters (dashboard uses "-" as sentinel for "not set")
    closure_reason = config.get("closure_reason") or None
    if closure_reason == "-":
        closure_reason = None
    closure_reason_description = config.get("closure_reason_description") or None
    if closure_reason_description == "-":
        closure_reason_description = None

    logger = utils.logger_for_input("update_cyberint_status")

    # Validate required fields
    if not account:
        logger.error("Missing required parameter: account")
        return 1
    if not instance_domain:
        logger.error("Missing required parameter: instance_domain")
        return 1
    if not client_name:
        logger.error("Missing required parameter: client_name")
        return 1
    if status not in VALID_STATUSES:
        logger.error(
            "Invalid status '%s'. Must be one of: %s",
            status,
            ", ".join(sorted(VALID_STATUSES)),
        )
        return 1
    if status == "closed" and not closure_reason:
        logger.error("closure_reason is required when status is 'closed'")
        return 1
    if closure_reason and closure_reason not in VALID_CLOSURE_REASONS:
        logger.error(
            "Invalid closure_reason '%s'. Must be one of: %s",
            closure_reason,
            ", ".join(sorted(VALID_CLOSURE_REASONS)),
        )
        return 1

    # Collect ref_ids from search results
    ref_ids = _extract_ref_ids(results_file, logger)
    if not ref_ids:
        logger.warning("No ref_id values found in search results. Nothing to update.")
        return 0

    logger.info("Collected %d unique ref_id(s) to update to status '%s'", len(ref_ids), status)

    # Build client
    try:
        api_key = utils.get_account_api_key(session_key, account)
        proxies = utils.get_proxy_settings(session_key)
        app_version = utils.get_version(session_key)
    except Exception as e:
        logger.error("Failed to retrieve credentials or settings: %s", e)
        return 1

    try:
        client = CyberintClient(
            version=app_version,
            client_name=client_name,
            instance_domain=instance_domain,
            access_token=api_key,
            input_name="update_cyberint_status",
            proxies=proxies or {},
        )
    except Exception as e:
        logger.error("Failed to create Cyberint API client: %s", e)
        return 1

    # Send updates in batches of MAX_BATCH_SIZE
    ref_id_list = list(ref_ids)
    for i in range(0, len(ref_id_list), MAX_BATCH_SIZE):
        batch = ref_id_list[i : i + MAX_BATCH_SIZE]
        try:
            client.update_alerts_status(
                alert_ref_ids=batch,
                status=status,
                closure_reason=closure_reason,
                closure_reason_description=closure_reason_description,
            )
            logger.info(
                "Successfully updated %d alert(s) (batch %d) to status '%s'",
                len(batch),
                (i // MAX_BATCH_SIZE) + 1,
                status,
            )
        except Exception as e:
            logger.error(
                "Failed to update batch %d (%d alerts): %s",
                (i // MAX_BATCH_SIZE) + 1,
                len(batch),
                e,
            )
            return 1

    logger.info("All %d alert(s) updated successfully.", len(ref_id_list))
    return 0


def _extract_ref_ids(results_file, logger):
    """Extract unique ref_id values from the Splunk results file (gzip CSV)."""
    ref_ids = set()
    if not results_file:
        return ref_ids

    try:
        with gzip.open(results_file, "rt") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ref_id = row.get("ref_id", "").strip()
                if ref_id:
                    ref_ids.add(ref_id)
    except Exception as e:
        logger.error("Error reading results file '%s': %s", results_file, e)

    return ref_ids


def main():
    payload = json.loads(sys.stdin.read())
    return run(payload)


if __name__ == "__main__":
    sys.exit(main())
