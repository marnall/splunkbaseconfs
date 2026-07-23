from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from html import unescape

import feedparser
import import_declare_test
import requests
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

ADDON_NAME = "WeAre_RSS_App_For_Splunk"
ADDON_VERSION = "1.0.0"
SETTINGS_CONF = "weare_rss_app_for_splunk_settings"
CHECKPOINT_COLLECTION = "rss_feed_checkpoints"
CHECKPOINT_KEY = "seen_entry_ids"
MAX_CHECKPOINT_IDS = 10000
TIMESTAMP_MODE_INDEXING = "indexing_time"
TIMESTAMP_MODE_FIELD = "feed_field"
TIMESTAMP_FIELD_PARSED_KEYS = {
    "published": ("published_parsed",),
    "updated": ("updated_parsed",),
    "created": ("created_parsed",),
}
ALLOWED_TIMESTAMP_FIELDS = frozenset(TIMESTAMP_FIELD_PARSED_KEYS)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_FIELDS = ("title", "summary", "content")


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def _get_checkpointer(session_key: str) -> checkpointer.KVStoreCheckpointer:
    return checkpointer.KVStoreCheckpointer(
        CHECKPOINT_COLLECTION,
        session_key,
        ADDON_NAME,
    )


def _load_seen_ids(ckpt: checkpointer.Checkpointer, input_name: str) -> set:
    state = ckpt.get(input_name)
    if not state:
        return set()
    try:
        if isinstance(state, str):
            payload = json.loads(state)
        else:
            payload = state
        return set(payload.get(CHECKPOINT_KEY, []))
    except (TypeError, json.JSONDecodeError, AttributeError):
        return set()


def _save_seen_ids(
    ckpt: checkpointer.Checkpointer, input_name: str, seen_ids: set
) -> None:
    ids = list(seen_ids)
    if len(ids) > MAX_CHECKPOINT_IDS:
        ids = ids[-MAX_CHECKPOINT_IDS:]
    ckpt.update(input_name, {CHECKPOINT_KEY: ids})


def _entry_link(entry: dict):
    link = entry.get("link")
    if link:
        return str(link)
    for item in entry.get("links", []):
        if not isinstance(item, dict):
            continue
        href = item.get("href")
        rel = item.get("rel", "alternate")
        if href and rel in (None, "alternate"):
            return str(href)
    return None


def _entry_id(entry: dict) -> str:
    entry_id = entry.get("id") or _entry_link(entry)
    if entry_id:
        return str(entry_id)
    title = entry.get("title", "")
    published = entry.get("published", entry.get("updated", ""))
    digest = hashlib.sha256(f"{title}|{published}".encode("utf-8")).hexdigest()
    return digest


def _entry_authors(entry: dict) -> list:
    authors = []
    author = entry.get("author")
    if author:
        authors.append(str(author))

    author_detail = entry.get("author_detail") or {}
    if isinstance(author_detail, dict):
        detail_name = author_detail.get("name")
        if detail_name and detail_name not in authors:
            authors.append(str(detail_name))

    for item in entry.get("authors", []):
        if isinstance(item, dict) and item.get("name"):
            name = str(item["name"])
            if name not in authors:
                authors.append(name)
    return authors


def _strip_html_tags(value) -> str | None:
    if value is None:
        return None
    text = str(value)
    if not text:
        return text
    text = unescape(_HTML_TAG_RE.sub(" ", text))
    return re.sub(r"\s+", " ", text).strip()


def _maybe_strip_html_fields(entry_dict: dict, strip_html_tags: bool) -> dict:
    if not strip_html_tags:
        return entry_dict
    for field in _HTML_FIELDS:
        if field in entry_dict:
            entry_dict[field] = _strip_html_tags(entry_dict[field])
    return entry_dict


def _serialize_entry(entry: dict, feed_format=None, strip_html_tags: bool = False) -> dict:
    tags = []
    for tag in entry.get("tags", []):
        if isinstance(tag, dict):
            tags.append(tag.get("term", ""))
        else:
            tags.append(str(tag))

    authors = _entry_authors(entry)

    content = None
    if entry.get("content"):
        content = entry["content"][0].get("value")
    elif entry.get("summary"):
        content = entry.get("summary")

    published = entry.get("published") or entry.get("updated")
    entry_dict = {
        "id": _entry_id(entry),
        "title": entry.get("title"),
        "link": _entry_link(entry),
        "summary": entry.get("summary"),
        "content": content,
        "published": published,
        "updated": entry.get("updated"),
        "created": entry.get("created"),
        "author": authors[0] if authors else None,
        "authors": authors,
        "tags": tags,
        "feed_format": feed_format,
    }
    return _maybe_strip_html_fields(entry_dict, strip_html_tags)


def _fetch_feed(
    logger: logging.Logger,
    url: str,
    verify_ssl: bool,
    http_timeout: int,
) -> feedparser.FeedParserDict:
    logger.info("Fetching feed from %s", url)
    response = requests.get(
        url,
        timeout=http_timeout,
        verify=verify_ssl,
        headers={"User-Agent": f"{ADDON_NAME}/{ADDON_VERSION}"},
    )
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if feed.bozo and feed.bozo_exception:
        logger.warning(
            "Feed parsed with warnings: %s", feed.bozo_exception
        )
    return feed


def _parse_time_struct(parsed) -> float:
    return float(time.mktime(parsed))


def _event_time(
    entry: dict,
    entry_dict: dict,
    timestamp_mode: str,
    timestamp_field: str,
    run_time: float,
    logger: logging.Logger,
) -> float:
    if timestamp_mode != TIMESTAMP_MODE_FIELD:
        return run_time

    field = (timestamp_field or "published").strip().lower()
    if field not in ALLOWED_TIMESTAMP_FIELDS:
        logger.warning(
            "Unknown timestamp_field '%s', using indexing time instead",
            timestamp_field,
        )
        return run_time

    for parsed_key in TIMESTAMP_FIELD_PARSED_KEYS[field]:
        parsed = entry.get(parsed_key)
        if parsed:
            try:
                return _parse_time_struct(parsed)
            except (OverflowError, ValueError, TypeError):
                pass

    raw_value = entry_dict.get(field)
    if raw_value:
        parsed = feedparser._parse_date(raw_value)
        if parsed:
            try:
                return _parse_time_struct(parsed)
            except (OverflowError, ValueError, TypeError):
                pass

    logger.warning(
        "Could not parse timestamp from field '%s', using indexing time instead",
        field,
    )
    return run_time


def validate_input(definition: smi.ValidationDefinition):
    parameters = definition.parameters
    url = parameters.get("url", "")
    if url and not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")

    http_timeout = parameters.get("http_timeout", "30")
    try:
        timeout_value = int(http_timeout)
    except (TypeError, ValueError) as exc:
        raise ValueError("HTTP timeout must be a positive integer.") from exc
    if timeout_value < 1 or timeout_value > 300:
        raise ValueError("HTTP timeout must be between 1 and 300 seconds.")

    timestamp_mode = parameters.get("timestamp_mode", TIMESTAMP_MODE_INDEXING)
    if timestamp_mode not in (TIMESTAMP_MODE_INDEXING, TIMESTAMP_MODE_FIELD):
        raise ValueError(
            "Event timestamp must be 'indexing_time' or 'feed_field'."
        )

    if timestamp_mode == TIMESTAMP_MODE_FIELD:
        timestamp_field = (parameters.get("timestamp_field") or "published").strip().lower()
        if timestamp_field not in ALLOWED_TIMESTAMP_FIELDS:
            allowed = ", ".join(sorted(ALLOWED_TIMESTAMP_FIELDS))
            raise ValueError(
                f"Timestamp field must be one of: {allowed}."
            )


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    session_key = inputs.metadata["session_key"]
    ckpt = _get_checkpointer(session_key)
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name=SETTINGS_CONF,
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            url = input_item.get("url")
            verify_ssl = bool(int(input_item.get("verify_ssl", "1")))
            http_timeout = int(input_item.get("http_timeout", "30"))
            index = input_item.get("index")
            sourcetype = input_item.get("sourcetype", "rss:feed")
            timestamp_mode = input_item.get("timestamp_mode", TIMESTAMP_MODE_INDEXING)
            timestamp_field = input_item.get("timestamp_field", "published")
            strip_html_tags = bool(int(input_item.get("strip_html_tags", "0")))

            feed = _fetch_feed(logger, url, verify_ssl, http_timeout)
            feed_format = getattr(feed, "version", None) or "unknown"
            run_time = time.time()
            seen_ids = _load_seen_ids(ckpt, normalized_input_name)
            new_events = 0

            for entry in feed.entries:
                entry_dict = _serialize_entry(
                    entry,
                    feed_format=feed_format,
                    strip_html_tags=strip_html_tags,
                )
                entry_key = entry_dict["id"]
                if entry_key in seen_ids:
                    continue

                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(entry_dict, ensure_ascii=False, default=str),
                        index=index,
                        sourcetype=sourcetype,
                        time=_event_time(
                            entry,
                            entry_dict,
                            timestamp_mode,
                            timestamp_field,
                            run_time,
                            logger,
                        ),
                    )
                )
                seen_ids.add(entry_key)
                new_events += 1

            _save_seen_ids(ckpt, normalized_input_name, seen_ids)
            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                new_events,
                index,
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "rss_feed_input_error",
                msg_before=(
                    "Exception raised while ingesting RSS/ATOM feed for "
                    f"{normalized_input_name}: "
                ),
            )
