import json
import logging
from typing import Any, Optional, Protocol

from solnlib import log
from splunklib import modularinput as smi

from astelia_api import AsteliaClient
from astelia_common import build_client, get_logger, input_name_from_stanza, parse_rfc3339

INPUT_KIND = "astelia_connectors"
SOURCETYPE = "astelia:connector"
DEFAULT_STALE_AFTER_HOURS = 24
MIN_STALE_AFTER_HOURS = 1
MAX_STALE_AFTER_HOURS = 168


class EventWriter(Protocol):
    def write_event(self, event: smi.Event) -> None: ...


def validate_input(definition: smi.ValidationDefinition) -> None:
    _stale_after_hours(definition.parameters.get("stale_after_hours"))


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    session_key = inputs.metadata["session_key"]
    for stanza, input_item in inputs.inputs.items():
        input_name = input_name_from_stanza(stanza)
        logger = get_logger(input_name, session_key)
        try:
            client = build_client(session_key, input_item["account"], logger)
            collect_connectors(
                client=client,
                event_writer=event_writer,
                input_name=input_name,
                account_name=input_item["account"],
                index=input_item.get("index"),
                stale_after_hours=_stale_after_hours(input_item.get("stale_after_hours")),
                logger=logger,
            )
        except Exception as exc:
            log.log_exception(logger, exc, "ConnectorsCollectionError", msg_before="Connector-health collection failed")


def collect_connectors(
    client: AsteliaClient,
    event_writer: EventWriter,
    input_name: str,
    account_name: str,
    index: Optional[str],
    stale_after_hours: int,
    logger: logging.Logger,
) -> int:
    snapshot = client.list_connectors(stale_after_hours=stale_after_hours)
    checked_at = snapshot.get("checked_at")
    event_time = f"{parse_rfc3339(checked_at):.3f}" if checked_at else None
    source = f"{INPUT_KIND}://{input_name}"
    rows: list[dict[str, Any]] = snapshot.get("data") or []
    for row in rows:
        event_data = dict(row)
        event_data["checked_at"] = checked_at
        event_writer.write_event(
            smi.Event(
                data=json.dumps(event_data, separators=(",", ":")),
                time=event_time,
                host=client.host,
                index=index,
                source=source,
                sourcetype=SOURCETYPE,
            )
        )
    log.events_ingested(logger, source, SOURCETYPE, len(rows), index, account=account_name, host=client.host)
    return len(rows)


def _stale_after_hours(raw_value: Optional[str]) -> int:
    if raw_value in (None, ""):
        return DEFAULT_STALE_AFTER_HOURS
    try:
        hours = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"stale_after_hours must be an integer between {MIN_STALE_AFTER_HOURS} and {MAX_STALE_AFTER_HOURS}"
        ) from exc
    if not MIN_STALE_AFTER_HOURS <= hours <= MAX_STALE_AFTER_HOURS:
        raise ValueError(f"stale_after_hours must be between {MIN_STALE_AFTER_HOURS} and {MAX_STALE_AFTER_HOURS}")
    return hours
