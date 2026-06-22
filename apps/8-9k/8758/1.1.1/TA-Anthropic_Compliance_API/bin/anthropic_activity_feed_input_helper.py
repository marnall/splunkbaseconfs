"""Modular input helper for Anthropic Compliance API - Activity Feed."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone

import import_declare_test  # noqa: F401  UCC sys.path bootstrap
import requests
from solnlib import conf_manager, log
from splunklib import modularinput as smi

ADDON_NAME = "TA-Anthropic_Compliance_API"
SOURCETYPE = "anthropic:compliance:activity"
API_BASE_URL = "https://api.anthropic.com/v1/compliance"
API_VERSION = "2026-03-29"
PAGE_LIMIT = 5000
DEFAULT_LOOKBACK_HOURS = 168


def get_logger() -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_activity_feed")


def get_account_config(session_key: str, account_name: str) -> dict:
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta-anthropic_compliance_api_account",
    )
    account_conf_file = cfm.get_conf("ta-anthropic_compliance_api_account")
    return account_conf_file.get(account_name)


def _load_checkpoint(checkpoint_dir: str, input_name: str) -> dict:
    path = os.path.join(checkpoint_dir, f"{input_name}_activity_feed.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def _save_checkpoint(checkpoint_dir: str, input_name: str, data: dict) -> None:
    path = os.path.join(checkpoint_dir, f"{input_name}_activity_feed.json")
    with open(path, "w") as f:
        json.dump(data, f)


def parse_api_time(time_str: str | None) -> float | None:
    """Parse ISO 8601 timestamp string to Unix epoch float."""
    if not time_str:
        return None
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return dt.timestamp()
    except ValueError:
        return None


def _get(
    logger: logging.Logger,
    api_key: str,
    url: str,
    params: dict,
) -> dict:
    """GET request with exponential backoff on 429."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
    }
    for attempt in range(5):
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("retry-after", 2 ** (attempt + 1)))
            logger.warning(
                "Rate limited; sleeping %ds (attempt %d)", retry_after, attempt + 1
            )
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("Exceeded retry limit for rate limiting")


def fetch_activities_initial(
    logger: logging.Logger,
    api_key: str,
    created_at_gte: str,
) -> tuple[list[dict], str | None, str | None]:
    """Fetch all activities since created_at_gte on first run.

    Returns events in oldest-first order, plus the first_id and first_created_at
    of the most recent event (for use as the next incremental checkpoint).
    """
    url = f"{API_BASE_URL}/activities"
    params: dict = {"limit": PAGE_LIMIT, "created_at.gte": created_at_gte}
    all_events: list[dict] = []

    # Activity Feed is newest-first; paginate backwards via after_id to reach oldest events
    while True:
        data = _get(logger, api_key, url, params)
        events: list[dict] = data.get("data", [])
        all_events.extend(events)
        logger.debug(
            "Fetched %d activities (total so far: %d)", len(events), len(all_events)
        )

        if not data.get("has_more") or not events:
            break
        # after_id continues backwards (older events)
        params["after_id"] = events[-1].get("id")

    if not all_events:
        return [], None, None

    # Reverse so oldest events are first for sequential ingestion
    all_events.reverse()

    # Checkpoint is the newest event (first in API response, last after reversal)
    newest = all_events[-1]
    return all_events, newest.get("id"), newest.get("created_at")


def fetch_activities_incremental(
    logger: logging.Logger,
    api_key: str,
    checkpoint_first_id: str,
    checkpoint_created_at: str,
) -> tuple[list[dict], str | None, str | None]:
    """Fetch activities newer than the saved checkpoint.

    Page 1 anchors with before_id=checkpoint_first_id, which positions the
    server-side cursor just past the checkpoint in the API's sort order
    (newest-first, ties broken by activity id). before_id and after_id
    are mutually exclusive per request, so subsequent pages walk toward
    older events with after_id=last_id and a local created_at filter is
    applied to bound the walk at the checkpoint.

    Returns events in oldest-first order, plus updated checkpoint values.
    """
    url = f"{API_BASE_URL}/activities"
    checkpoint_ts = parse_api_time(checkpoint_created_at)
    params: dict = {"limit": PAGE_LIMIT, "before_id": checkpoint_first_id}
    all_new_events: list[dict] = []

    while True:
        data = _get(logger, api_key, url, params)
        raw_events: list[dict] = data.get("data", [])

        # Apply the checkpoint bound only on after_id pages; before_id is
        # already a server-side bound.
        if "after_id" in params and checkpoint_ts is not None:
            kept = [
                e
                for e in raw_events
                if (parse_api_time(e.get("created_at")) or 0) > checkpoint_ts
            ]
        else:
            kept = raw_events

        all_new_events.extend(kept)
        logger.debug(
            "Fetched %d activities (%d within window; total: %d)",
            len(raw_events),
            len(kept),
            len(all_new_events),
        )

        if not data.get("has_more") or not kept:
            break

        # Advance the cursor from the raw last_id so we continue from the
        # actual server position, not from the filtered result.
        params = {"limit": PAGE_LIMIT, "after_id": raw_events[-1].get("id")}

    if not all_new_events:
        return [], None, None

    all_new_events.reverse()
    newest = all_new_events[-1]
    return all_new_events, newest.get("id"), newest.get("created_at")


def validate_input(definition: smi.ValidationDefinition) -> None:
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    logger = get_logger()
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="ta-anthropic_compliance_api_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            account_config = get_account_config(session_key, input_item.get("account"))
            api_key = account_config.get("api_key")
            checkpoint_dir = inputs.metadata.get("checkpoint_dir", "/tmp")
            checkpoint = _load_checkpoint(checkpoint_dir, normalized_input_name)

            lookback_hours = int(
                input_item.get("lookback_hours") or DEFAULT_LOOKBACK_HOURS
            )

            if checkpoint.get("first_id"):
                logger.info(
                    "Incremental run: checkpoint first_id=%s created_at=%s",
                    checkpoint["first_id"],
                    checkpoint.get("first_created_at"),
                )
                events, new_first_id, new_first_created_at = (
                    fetch_activities_incremental(
                        logger,
                        api_key,
                        checkpoint["first_id"],
                        checkpoint["first_created_at"],
                    )
                )
            else:
                lookback_ts = datetime.now(timezone.utc).timestamp() - (
                    lookback_hours * 3600
                )
                created_at_gte = datetime.fromtimestamp(
                    lookback_ts, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
                logger.info("Initial run: fetching activities since %s", created_at_gte)
                events, new_first_id, new_first_created_at = fetch_activities_initial(
                    logger, api_key, created_at_gte
                )

            index = input_item.get("index")
            for event in events:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(event, ensure_ascii=False, default=str),
                        index=index,
                        sourcetype=SOURCETYPE,
                    )
                )

            if new_first_id:
                _save_checkpoint(
                    checkpoint_dir,
                    normalized_input_name,
                    {
                        "first_id": new_first_id,
                        "first_created_at": new_first_created_at,
                    },
                )

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE,
                len(events),
                index,
                account=input_item.get("account"),
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            logger.error(
                "Exception raised while ingesting Activity Feed data: %s: %s",
                type(e).__name__,
                e,
                exc_info=True,
            )
