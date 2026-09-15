"""Scheduled event ingestion script for the Flare Splunk integration."""

import json
import os
import sys

from datetime import datetime
from datetime import timezone
from typing import Optional


if sys.version_info < (3, 7):
    sys.exit("Error: This application requires Python 3.7 or higher.")

sys.path.insert(0, os.path.dirname(__file__))

# Ensure the vendored lib directory is on the path for flareio SDK
_LIB_DIR = os.path.join(os.path.dirname(__file__), "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

import flare_constants as const

from checkpoint_manager import load_checkpoint
from checkpoint_manager import reconcile_checkpoint_with_config
from checkpoint_manager import save_checkpoint
from flare_external_requests import enrich_event_with_full_details
from flare_external_requests import fetch_events_by_paginating
from flare_logger import setup_logger
from flare_sdk_client import create_flare_client
from ingestion_config import parse_ingestion_config
from splunk_storage import get_all_storage_values
from splunk_storage import get_session_token_from_stdin
from splunk_storage import get_storage_passwords


logger = setup_logger()


def main() -> None:
    """Main entry point for the cron job."""
    logger.debug(
        "The Flare app has woken up and is beginning its scheduled "
        "data collection routine."
    )

    #   1: Authenticate with Splunk
    splunk_session_token = get_session_token_from_stdin()

    if not splunk_session_token:
        logger.critical(
            "We couldn't securely identify this session. "
            "Please make sure the app is fully configured."
        )
        return

    storage_passwords = get_storage_passwords(splunk_session_token)
    if not storage_passwords:
        logger.info(
            "We couldn't find your saved app configuration. "
            "Please visit the setup page to save your credentials."
        )
        return

    #   2: Parse all config in one go
    config = get_all_storage_values(storage_passwords)
    ingestion_cfg = parse_ingestion_config(config)
    if ingestion_cfg is None:
        return  # parse_ingestion_config already logged the reason

    api_key = ingestion_cfg["api_key"]
    tenant_ids = ingestion_cfg["tenant_ids"]
    tenant_names_map = ingestion_cfg["tenant_names_map"]
    ingest_full = ingestion_cfg["ingest_full_event_data"]
    sev_filter = ingestion_cfg["severities_filter"]
    type_filter = ingestion_cfg["source_types_filter"]
    backfill_days = ingestion_cfg["backfill_days"]
    backfill_start = ingestion_cfg["backfill_start_date"]
    proxies = ingestion_cfg["proxies"]
    ssl_verify = ingestion_cfg["ssl_verify"]
    index_name = ingestion_cfg["index_name"]
    log_level = ingestion_cfg["log_level"]

    logger.debug(
        "Successfully loaded configuration and applied logging level: %s", log_level
    )

    #   3: Checkpoint management
    checkpoint = load_checkpoint()
    checkpoint = reconcile_checkpoint_with_config(checkpoint, backfill_days, index_name)

    #   4: Build the Flare API client (official SDK)
    client = create_flare_client(
        api_key=api_key,
        proxies=proxies,
        ssl_verify=ssl_verify,
    )

    #   5: Ingest events per tenant
    total_events = 0

    for tenant_id in tenant_ids:
        tenant_key = str(tenant_id)
        tenant_name = tenant_names_map.get(tenant_key) or tenant_names_map.get(
            tenant_id, tenant_key
        )
        tenant_checkpoint = checkpoint.get(tenant_key, {})
        from_token: Optional[str] = tenant_checkpoint.get("last_next_token")
        last_valid_cursor = from_token
        tenant_events = 0

        if from_token:
            start_date = backfill_start
            logger.info("Resuming search for %s from checkpoint.", tenant_name)
        else:
            last_run_utc = tenant_checkpoint.get("last_run_utc")
            start_date = last_run_utc if last_run_utc else backfill_start
            logger.info(
                "Starting fresh polling for %s back to %s.", tenant_name, start_date
            )

        while True:
            result = fetch_events_by_paginating(
                client,
                from_token=from_token,
                size=const.DEFAULT_INGESTION_PAGE_SIZE,
                severities=sev_filter or None,
                source_types=type_filter or None,
                start_date=start_date,
            )

            items = result.get("items", [])
            next_token = result.get("next")

            if next_token:
                last_valid_cursor = next_token

            for event in items:
                if ingest_full:
                    event = enrich_event_with_full_details(event, client)

                metadata_obj = event.get("metadata", {})
                event_timestamp = metadata_obj.get("matched_at") or metadata_obj.get(
                    "estimated_created_at"
                )

                final_event = {"timestamp": event_timestamp}
                final_event.update(event)
                final_event["tenant_id"] = tenant_id
                final_event["tenant_name"] = tenant_name

                print(json.dumps(final_event), flush=True)
                logger.debug(
                    "Successfully ingested event UID %s for tenant %s",
                    metadata_obj.get("uid"),
                    tenant_name,
                )

                tenant_events += 1

            if not next_token or not items:
                logger.info(
                    "Pagination complete for %s. Reached end of feed. Events: %d",
                    tenant_name,
                    tenant_events,
                )
                last_valid_cursor = None
                break

            from_token = next_token
            logger.info(
                "Collected %d events. Next page for %s...", len(items), tenant_name
            )

        if tenant_events == 0:
            logger.info("No new events for %s.", tenant_name)
        else:
            logger.info(
                "Finished tasks for %s. Events sent: %d.", tenant_name, tenant_events
            )
        total_events += tenant_events

        checkpoint[tenant_key] = {
            "last_next_token": last_valid_cursor,
            # re-checks from the same point and doesn't miss delayed events.
            "last_run_utc": (
                datetime.now(timezone.utc)
                .replace(microsecond=0)
                .strftime("%Y-%m-%dT%H:%M:%SZ")
                if tenant_events > 0
                else tenant_checkpoint.get(
                    "last_run_utc",
                    datetime.now(timezone.utc)
                    .replace(microsecond=0)
                    .strftime("%Y-%m-%dT%H:%M:%SZ"),
                )
            ),
            "events_ingested": tenant_events,
        }
        save_checkpoint(checkpoint)

    if total_events == 0:
        logger.info("Application completed. No new events found.")
    else:
        logger.info(
            "Application completed. Events ingested: %d into index: %s",
            total_events,
            index_name,
        )


if __name__ == "__main__":
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        main()
    except Exception as e:
        logger.critical("Unexpected error stopped the app: %s", e, exc_info=True)
    sys.exit(0)
