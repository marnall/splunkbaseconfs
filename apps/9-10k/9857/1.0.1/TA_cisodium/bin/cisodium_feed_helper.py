"""
The `cisodium_feed` modular input: pull one Cisodium feed into one index.

Each input names an account (a Cisodium URL and an API key), a feed and an
optional start date. A run reads pages from the checkpoint onwards, writes one
event per record, and saves the page's `next_cursor` after the page's events
are written — so a crash re-reads at most one page, and never skips one.

The checkpoint lives in the KV store (collection `ta_cisodium_checkpoints`),
keyed by the input's name. It remembers which URL and feed it belongs to: when
an input is repointed at another tenant or feed it starts over instead of
continuing from a position that means nothing there.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

import import_declare_test  # noqa: F401  (UCC: puts ../lib on sys.path)
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from cisodium_client import (
    DEFAULT_PAGE_SIZE,
    FEEDS,
    MAX_PAGE_SIZE,
    CisodiumClient,
    CisodiumError,
    parse_timestamp,
    proxies_from_settings,
    start_date_to_since,
)

ADDON_NAME = "TA_cisodium"
ACCOUNT_CONF = "ta_cisodium_account"
SETTINGS_CONF = "ta_cisodium_settings"
CHECKPOINT_COLLECTION = "ta_cisodium_checkpoints"

#: A run stops paging after this share of its interval, so runs never overlap.
RUN_BUDGET_SHARE = 0.8
MAX_RUN_SECONDS = 3000
MAX_PAGES_PER_RUN = 200


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger("%s_%s" % (ADDON_NAME.lower(), input_name))


def _conf_manager(session_key: str, conf_name: str) -> conf_manager.ConfManager:
    return conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm="__REST_CREDENTIAL__#%s#configs/conf-%s" % (ADDON_NAME, conf_name),
    )


def get_account(session_key: str, account_name: str) -> Dict[str, Any]:
    conf = _conf_manager(session_key, ACCOUNT_CONF).get_conf(ACCOUNT_CONF)
    return conf.get(account_name)


def get_proxy_settings(session_key: str) -> Optional[Dict[str, Any]]:
    try:
        conf = _conf_manager(session_key, SETTINGS_CONF).get_conf(SETTINGS_CONF)
        return conf.get("proxy")
    except Exception:  # no proxy stanza saved yet
        return None


def _page_size(value: Any) -> int:
    try:
        size = int(str(value).strip() or DEFAULT_PAGE_SIZE)
    except ValueError:
        return DEFAULT_PAGE_SIZE
    return max(1, min(size, MAX_PAGE_SIZE))


def _run_deadline(interval: Any) -> float:
    try:
        seconds = float(interval)
    except (TypeError, ValueError):
        seconds = 300.0
    budget = max(30.0, min(MAX_RUN_SECONDS, seconds * RUN_BUDGET_SHARE))
    return time.monotonic() + budget


#: Names Splunk gives its own meaning at search time. A JSON field called
#: `source` (a vulnerability's scanner, an incident's origin) would be mixed up
#: with the event's source, so these are renamed `cisodium_<name>`.
RESERVED_FIELDS = frozenset({
    "host", "source", "sourcetype", "index", "splunk_server", "eventtype",
    "tag", "linecount", "punct", "timestartpos", "timeendpos",
})


def without_nulls(value: Any) -> Any:
    """JSON without its null members.

    Splunk extracts a JSON null as the string "null": a present field whose
    value is "null" defeats coalesce(), matches `field=*` and shows up in every
    stats. An absent field is what "no value" means to Splunk.
    """
    if isinstance(value, dict):
        return {k: without_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [without_nulls(v) for v in value if v is not None]
    return value


def to_event(
    item: Dict[str, Any],
    *,
    feed: str,
    base_url: str,
    host: str,
    index: Optional[str],
) -> smi.Event:
    """One Cisodium record → one Splunk event (JSON, `_time` = when it changed)."""
    record = {
        ("cisodium_" + key if key in RESERVED_FIELDS else key): value
        for key, value in without_nulls(item).items()
    }
    ui_path = record.get("ui_path")
    if isinstance(ui_path, str) and ui_path.startswith("/"):
        # Not `url`: that is a CIM field with its own meaning (a URL involved
        # in the event), and the Vulnerabilities data model reads it.
        record["cisodium_url"] = base_url + ui_path
    else:
        record.pop("ui_path", None)  # audit entries have no page of their own
    moment = parse_timestamp(record.get("event_time"))
    return smi.Event(
        data=json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=str),
        time="%.6f" % moment if moment is not None else None,
        index=index,
        host=host,
        sourcetype=FEEDS[feed]["sourcetype"],
        done=True,
        unbroken=True,
    )


def validate_input(definition: smi.ValidationDefinition) -> None:
    params = definition.parameters
    feed = (params.get("feed") or "").strip()
    if feed not in FEEDS:
        raise ValueError("Choose one of the Cisodium feeds: %s" % ", ".join(sorted(FEEDS)))
    start_date_to_since(params.get("start_date"))
    size = str(params.get("page_size") or "").strip()
    if size and not (size.isdigit() and 1 <= int(size) <= MAX_PAGE_SIZE):
        raise ValueError("Page size must be a whole number from 1 to %d" % MAX_PAGE_SIZE)


def collect(
    *,
    client: CisodiumClient,
    feed: str,
    state: Dict[str, Any],
    since: Optional[str],
    page_size: int,
    deadline: Optional[float],
    write: Any,
    save: Any,
    logger: logging.Logger,
    max_pages: int = MAX_PAGES_PER_RUN,
) -> int:
    """Read pages from the checkpoint on; `write` each record, `save` each cursor.

    Returns the number of records written. Kept free of Splunk objects so the
    tests can drive the exact loop the input runs.
    """
    cursor = state.get("cursor")
    written = 0
    for page in client.iter_pages(
        feed,
        cursor=cursor,
        since=None if cursor else since,
        limit=page_size,
        max_pages=max_pages,
        deadline=deadline,
    ):
        items = page.get("items") or []
        for item in items:
            if isinstance(item, dict):
                write(item)
                written += 1
        next_cursor = page.get("next_cursor")
        if next_cursor and next_cursor != cursor:
            cursor = next_cursor
            save(cursor)
        logger.debug("feed=%s page_items=%d has_more=%s", feed, len(items), page.get("has_more"))
    return written


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    session_key = inputs.metadata["session_key"]
    for input_name, input_item in inputs.inputs.items():
        name = input_name.split("/")[-1]
        logger = logger_for_input(name)
        try:
            logger.setLevel(
                conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=ADDON_NAME,
                    conf_name=SETTINGS_CONF,
                )
            )
            log.modular_input_start(logger, name)
            feed = (input_item.get("feed") or "").strip()
            if feed not in FEEDS:
                raise ValueError("Input %s has no valid feed (%r)" % (name, feed))
            account_name = input_item.get("account")
            account = get_account(session_key, account_name)
            client = CisodiumClient(
                account.get("url"),
                account.get("api_key"),
                proxies=proxies_from_settings(get_proxy_settings(session_key)),
                logger=logger,
            )
            index = input_item.get("index")

            store = checkpointer.KVStoreCheckpointer(
                CHECKPOINT_COLLECTION, session_key, ADDON_NAME
            )
            state = store.get(name) or {}
            if state.get("base_url") != client.base_url or state.get("feed") != feed:
                if state:
                    logger.info(
                        "Input %s now reads %s from %s; starting that feed from the start "
                        "date instead of the old checkpoint.", name, feed, client.base_url,
                    )
                state = {}

            def write(item: Dict[str, Any]) -> None:
                event_writer.write_event(
                    to_event(item, feed=feed, base_url=client.base_url, host=client.host, index=index)
                )

            def save(cursor: str) -> None:
                store.update(
                    name,
                    {
                        "cursor": cursor,
                        "base_url": client.base_url,
                        "feed": feed,
                        "saved_at": int(time.time()),
                    },
                )

            written = collect(
                client=client,
                feed=feed,
                state=state,
                since=start_date_to_since(input_item.get("start_date")),
                page_size=_page_size(input_item.get("page_size")),
                deadline=_run_deadline(input_item.get("interval")),
                write=write,
                save=save,
                logger=logger,
            )
            log.events_ingested(
                logger,
                input_name,
                FEEDS[feed]["sourcetype"],
                written,
                index,
                account=account_name,
                host=client.host,
            )
            log.modular_input_end(logger, name)
        except CisodiumError as exc:
            log.log_exception(
                logger, exc, "Cisodium API error",
                msg_before="Input %s could not read from Cisodium: " % name,
            )
        except Exception as exc:  # keep the other inputs of this run going
            log.log_exception(
                logger, exc, "Cisodium input error",
                msg_before="Input %s failed: " % name,
            )
