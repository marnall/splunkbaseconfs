import json
import logging
from typing import Any, Optional, Protocol

from solnlib import log
from splunklib import modularinput as smi

from astelia_api import AsteliaClient, AsteliaInvalidCursorError
from astelia_common import (
    build_client,
    get_checkpointer,
    get_logger,
    input_name_from_stanza,
    parse_rfc3339,
)

INPUT_KIND = "astelia_audit_logs"
SOURCETYPE = "astelia:audit"
DEFAULT_PAGE_SIZE = 500
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 1000
MAX_PAGES_PER_RUN = 200


class Checkpointer(Protocol):
    def get(self, key: str) -> Optional[dict[str, Any]]: ...

    def update(self, key: str, state: dict[str, Any]) -> None: ...


class EventWriter(Protocol):
    def write_event(self, event: smi.Event) -> None: ...


def validate_input(definition: smi.ValidationDefinition) -> None:
    parameters = definition.parameters
    start_from = parameters.get("start_from")
    if start_from:
        try:
            parse_rfc3339(start_from)
        except ValueError as exc:
            raise ValueError(f"start_from must be an RFC 3339 timestamp: {exc}") from exc
    _page_size(parameters.get("page_size"))


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    session_key = inputs.metadata["session_key"]
    for stanza, input_item in inputs.inputs.items():
        input_name = input_name_from_stanza(stanza)
        logger = get_logger(input_name, session_key)
        try:
            client = build_client(session_key, input_item["account"], logger)
            collect_audit_logs(
                client=client,
                checkpointer=get_checkpointer(session_key),
                event_writer=event_writer,
                input_name=input_name,
                account_name=input_item["account"],
                index=input_item.get("index"),
                start_from=input_item.get("start_from") or None,
                page_size=_page_size(input_item.get("page_size")),
                logger=logger,
            )
        except Exception as exc:
            log.log_exception(logger, exc, "AuditLogsCollectionError", msg_before="Audit-log collection failed")


def collect_audit_logs(
    client: AsteliaClient,
    checkpointer: Checkpointer,
    event_writer: EventWriter,
    input_name: str,
    account_name: str,
    index: Optional[str],
    start_from: Optional[str],
    page_size: int,
    logger: logging.Logger,
) -> int:
    state = checkpointer.get(input_name) or {}
    cursor: Optional[str] = state.get("cursor")
    since: Optional[str] = state.get("last_occurred_at") or start_from
    source = f"{INPUT_KIND}://{input_name}"
    cursor_was_reset = False
    written = 0

    for _ in range(MAX_PAGES_PER_RUN):
        try:
            page = client.list_audit_logs(cursor=cursor, since=None if cursor else since, limit=page_size)
        except AsteliaInvalidCursorError:
            if cursor is None or cursor_was_reset:
                raise
            logger.warning(
                "audit_cursor_rejected",
                extra={"input": input_name, "resume_from": since},
            )
            cursor = None
            cursor_was_reset = True
            continue

        events = page.get("data") or []
        for event in events:
            event_writer.write_event(
                smi.Event(
                    data=json.dumps(event, separators=(",", ":")),
                    time=f"{parse_rfc3339(event['occurred_at']):.3f}",
                    host=client.host,
                    index=index,
                    source=source,
                    sourcetype=SOURCETYPE,
                )
            )
        pagination = page.get("pagination") or {}
        if events:
            last_event = events[-1]
            state = {
                "cursor": pagination.get("next_cursor"),
                "last_id": last_event.get("id"),
                "last_occurred_at": last_event.get("occurred_at"),
            }
            checkpointer.update(input_name, state)
            cursor = state["cursor"]
            since = state["last_occurred_at"]
        written += len(events)
        log.events_ingested(logger, source, SOURCETYPE, len(events), index, account=account_name, host=client.host)
        if not pagination.get("has_more"):
            break

    return written


def _page_size(raw_value: Optional[str]) -> int:
    if raw_value in (None, ""):
        return DEFAULT_PAGE_SIZE
    try:
        page_size = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"page_size must be an integer between {MIN_PAGE_SIZE} and {MAX_PAGE_SIZE}") from exc
    if not MIN_PAGE_SIZE <= page_size <= MAX_PAGE_SIZE:
        raise ValueError(f"page_size must be between {MIN_PAGE_SIZE} and {MAX_PAGE_SIZE}")
    return page_size
