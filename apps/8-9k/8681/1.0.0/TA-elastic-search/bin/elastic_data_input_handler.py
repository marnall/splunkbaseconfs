from __future__ import annotations

import datetime
import json
import logging
import re

from elasticsearch import Elasticsearch
from solnlib import conf_manager
from solnlib.modular_input.checkpointer import KVStoreCheckpointer
from splunklib import modularinput as smi

import import_declare_test  # noqa: F401 — sets up sys.path for lib/
import logger_manager

ADDON_NAME = "TA-elastic-search"
DEFAULT_START_TIME = "now-24h"
SOURCETYPE = "elasticsearch:json"
_NANOSECONDS_RE = re.compile(r"(\.\d{6})\d+")


def _to_epoch(ts: str) -> float | None:
    if not ts:
        return None
    try:
        val = float(ts)
        # Heuristic: values > 1e10 are milliseconds
        return val / 1000.0 if val > 1e10 else val
    except (ValueError, TypeError):
        pass
    try:
        normalized = _NANOSECONDS_RE.sub(r"\1", ts.replace("Z", "+00:00"))
        dt = datetime.datetime.fromisoformat(normalized)
        return dt.timestamp()
    except (ValueError, AttributeError):
        pass
    return None


def validate_input(session_key: str, input_script: smi.Script, definition: smi.ValidationDefinition):
    advanced_filter = (definition.parameters.get("advanced_filter_query") or "").strip()
    if advanced_filter:
        try:
            json.loads(advanced_filter)
        except json.JSONDecodeError as e:
            raise ValueError(f"Advanced Filter Query is not valid JSON: {e}")


def _get_account(session_key: str, account_name: str) -> dict:
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta-elastic-search_account",
    )
    return cfm.get_conf("ta-elastic-search_account").get(account_name)


def _get_es_client(account: dict, logger: logging.Logger) -> Elasticsearch:
    use_https = str(account.get("use_https", "1")) not in ("0", "false")
    verify_ssl = str(account.get("verify_ssl", "1")) not in ("0", "false")
    scheme = "https" if use_https else "http"
    host = account.get("host")
    port = int(account.get("port", 9200))
    username = account.get("username")
    password = account.get("password")

    logger.debug(f"Connecting to Elasticsearch: {scheme}://{host}:{port} verify_ssl={verify_ssl}")

    return Elasticsearch(
        f"{scheme}://{host}:{port}",
        basic_auth=(username, password),
        verify_certs=verify_ssl,
    )


def _build_query(time_field: str, since: str, advanced_filter_json: str) -> dict:
    query: dict = {
        "bool": {
            "must": [{"range": {time_field: {"gt": since}}}]
        }
    }
    if advanced_filter_json:
        query["bool"]["filter"] = json.loads(advanced_filter_json)
    return query


def _collect_events(
    logger: logging.Logger,
    es_client: Elasticsearch,
    event_writer: smi.EventWriter,
    input_item: dict,
    checkpointer: KVStoreCheckpointer,
    checkpoint_key: str,
) -> int:
    es_index = input_item.get("es_index")
    time_field = input_item.get("time_field") or "@timestamp"
    batch_size = max(500, min(int(input_item.get("batch_size") or 10000), 50000))
    advanced_filter = (input_item.get("advanced_filter_query") or "").strip()
    start_time = (input_item.get("start_time") or "").strip()
    splunk_index = input_item.get("index")

    state = checkpointer.get(checkpoint_key) or {}
    since = state.get("last_timestamp") or start_time or DEFAULT_START_TIME

    logger.info(f"Fetching from es_index={es_index} since={since} checkpoint={'resumed' if state else 'fresh start'}")

    # keep_alive is refreshed on every search call; only expires if a single batch write to Splunk takes >5m
    pit = es_client.open_point_in_time(index=es_index, keep_alive="5m")
    pit_id = pit["id"]

    query = _build_query(time_field, since, advanced_filter)
    logger.debug(f"Elasticsearch query: {json.dumps(query)}")
    sort = [{time_field: {"order": "asc"}}, {"_shard_doc": {"order": "asc"}}]
    last_sort = None
    total = 0
    page = 0

    try:
        while True:
            search_kwargs: dict = {
                "query": query,
                "sort": sort,
                "size": batch_size,
                "pit": {"id": pit_id, "keep_alive": "5m"},
                "track_total_hits": page == 0,
            }
            if last_sort:
                search_kwargs["search_after"] = last_sort

            response = es_client.search(**search_kwargs)
            pit_id = response["pit_id"]
            page += 1

            hits = response["hits"]["hits"]
            if not hits:
                break

            if page == 1:
                total_hits = response['hits']['total']['value']
                total_relation = response['hits']['total']['relation']
                qualifier = "at least " if total_relation == "gte" else ""
                logger.info(f"Total matching documents in Elasticsearch: {qualifier}{total_hits}")

            for hit in hits:
                raw_ts = hit["_source"].get(time_field, "")
                epoch = _to_epoch(raw_ts)
                if epoch is None and raw_ts:
                    logger.warning(f"Could not parse time_field '{time_field}' value '{raw_ts}' as a timestamp; event will have no time set")
                event_kwargs: dict = {
                    "data": json.dumps(hit["_source"], ensure_ascii=False, default=str),
                    "index": splunk_index,
                    "sourcetype": SOURCETYPE,
                }
                if epoch is not None:
                    event_kwargs["time"] = epoch
                event_writer.write_event(smi.Event(**event_kwargs))

            total += len(hits)
            last_sort = hits[-1]["sort"]
            last_timestamp = hits[-1]["_source"].get(time_field, "")

            if last_timestamp:
                checkpointer.update(checkpoint_key, {"last_timestamp": last_timestamp})
            else:
                logger.warning(
                    f"time_field '{time_field}' missing from last document in batch; "
                    "skipping checkpoint update to avoid re-ingestion on next run"
                )

            logger.info(f"Page {page}: {len(hits)} events ingested, running_total={total}, last_timestamp={last_timestamp}")

            if len(hits) < batch_size:
                break

    finally:
        try:
            es_client.close_point_in_time(id=pit_id)
        except Exception as e:
            logger.warning(f"Failed to close PIT: {e}")

    return total


def stream_events(session_key: str, input_script: smi.Script, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_manager.setup_logging(normalized_input_name)

        try:
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="ta-elastic-search_settings",
            )
            logger.setLevel(log_level)
            for handler in logger.handlers:
                handler.setLevel(log_level)

            logger.info(f"Starting input: {normalized_input_name}")

            account = _get_account(session_key, input_item.get("account"))
            es_client = _get_es_client(account, logger)

            checkpointer = KVStoreCheckpointer(
                "ta_elastic_search_checkpoints", session_key, ADDON_NAME
            )

            try:
                total = _collect_events(
                    logger, es_client, event_writer, input_item, checkpointer, normalized_input_name
                )
            finally:
                es_client.close()

            logger.info(f"Completed input: {normalized_input_name}, total events ingested: {total}")

        except Exception as e:
            logger.error(f"Error in input {normalized_input_name}: {e}", exc_info=True)
