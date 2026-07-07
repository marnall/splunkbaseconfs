import json
import logging
from typing import Optional

import import_declare_test
from ipfabric import IPFClient
from ipf_retrievers import fetch_table
from solnlib import conf_manager, log
from splunklib import modularinput as smi


ADDON_NAME = "TA-ip_fabric"
# ucc-gen lowercases the add-on name for the settings conf, so the actual conf
# file / endpoint is `ta-ip_fabric_settings` (see the generated
# TA-ip_fabric_rh_settings.py: MultipleModel('ta-ip_fabric_settings', ...)).
SETTINGS_CONF_NAME = "ta-ip_fabric_settings"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def _conf(session_key: str):
    return conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{SETTINGS_CONF_NAME}",
    ).get_conf(SETTINGS_CONF_NAME)


def get_addon_settings(session_key: str) -> dict:
    return _conf(session_key).get("settings")


def get_proxy_settings(session_key: str) -> dict:
    try:
        return _conf(session_key).get("proxy") or {}
    except Exception:
        return {}


def _truthy(v) -> bool:
    return str(v).lower() in ("1", "true", "yes")


def build_proxy(proxy: dict) -> Optional[dict]:
    """Return a niquests-compatible proxy mapping or None if disabled/incomplete."""
    if not proxy or not _truthy(proxy.get("proxy_enabled")):
        return None
    host = (proxy.get("proxy_url") or "").strip()
    port = (proxy.get("proxy_port") or "").strip()
    if not host or not port:
        return None
    scheme = (proxy.get("proxy_type") or "http").strip().lower()
    if scheme == "socks5" and _truthy(proxy.get("proxy_rdns")):
        scheme = "socks5h"
    user = (proxy.get("proxy_username") or "").strip()
    password = (proxy.get("proxy_password") or "")
    auth = f"{user}:{password}@" if user else ""
    url = f"{scheme}://{auth}{host}:{port}"
    return {"http": url, "https": url}


def build_ipf_client(
        logger: logging.Logger,
        settings: dict,
        ipf_url: str,
        snapshot_id: str,
        proxy: Optional[dict] = None,
) -> IPFClient:
    cert_path = settings.get("cert_path") or None
    timeout = int(settings.get("client_timeout") or 20)
    logger.info(
        f'Building IPFClient to {ipf_url} (proxy={bool(proxy)}')
    kwargs = dict(
        base_url=ipf_url,
        auth=settings["ipf_token"],
        snapshot_id=snapshot_id or "$last",
        timeout=timeout,
        verify=cert_path if cert_path else False,
    )
    if proxy:
        kwargs["proxy"] = proxy
    return IPFClient(**kwargs)


def fetch_for_input(
    logger: logging.Logger,
    client: IPFClient,
    table_path: str,
    load_intent_checks: bool,
    only_count: bool,
    table_filter: Optional[dict] = None,
):
    if only_count:
        count = client.get_count(table_path, filters=table_filter)
        logger.info("IPF count for %s (filter=%s): %d", table_path, bool(table_filter), count)
        return [{
            "table": table_path,
            "count": count,
        }]
    logger.info(
        "Fetching %s (intent_checks=%s, filter=%s)",
        table_path, load_intent_checks, bool(table_filter),
    )
    return fetch_table(
        client,
        table_path,
        filters=table_filter,
        reports=bool(load_intent_checks),
    )


def enrich_with_snapshot(
    row: dict,
    client: IPFClient,
    use_ipf_timestamp: bool,
    strftime_format: str,
) -> dict:
    """Stamp snapshot identity (always) and snapshot-end timestamp variants
    (only when use_ipf_timestamp) onto an event row.

    Field shape matches TA-ip_fabric: snapshot_id, snapshot_time_ms,
    snapshot_time, snapshot_time_iso.
    """
    out = {**row, "snapshot_id": client.snapshot_id}
    snapshot_end = client.snapshot.end if client.snapshot else None
    if use_ipf_timestamp and snapshot_end:
        ts_seconds = snapshot_end.timestamp()
        out["snapshot_time_ms"] = int(ts_seconds * 1000)
        out["snapshot_time"] = snapshot_end.strftime(strftime_format)
        out["snapshot_time_iso"] = snapshot_end.isoformat()
    return out


def validate_input(definition: smi.ValidationDefinition):
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name=SETTINGS_CONF_NAME,
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            settings = get_addon_settings(session_key)
            proxy_settings = get_proxy_settings(session_key)
            proxy = build_proxy(proxy_settings)
            ipf_url = input_item.get("ipf_url")

            if ipf_url.endswith('change.this'):
                logger.warning(f"Source url for {normalized_input_name} is not yet configured.")
                continue
            snapshot_id = input_item.get("snapshot_id") or "$last"
            table_path = input_item.get("table_path")
            use_ipf_timestamp = _truthy(input_item.get("use_ipf_timestamp"))
            load_intent_checks = _truthy(input_item.get("load_intent_checks"))
            only_count = _truthy(input_item.get("only_count"))
            strftime_format = settings.get("strftime_format") or "%Y-%m-%dT%H:%M:%SZ"

            table_filter_raw = (input_item.get("table_filter") or "").strip()
            try:
                table_filter = json.loads(table_filter_raw) if table_filter_raw else None
            except json.JSONDecodeError as e:
                logger.error("Invalid table_filter JSON, ignoring: %s (%s)", table_filter_raw, e)
                table_filter = None

            client = build_ipf_client(logger, settings, ipf_url, snapshot_id, proxy=proxy)
            data = fetch_for_input(
                logger, client,
                table_path, load_intent_checks, only_count, table_filter,
            )

            snapshot_end = client.snapshot.end if client.snapshot else None
            event_time = snapshot_end.timestamp() if (use_ipf_timestamp and snapshot_end) else None

            sourcetype = "ipfabric:table"
            index = input_item.get("index")
            for row in data:
                enriched = enrich_with_snapshot(row, client, use_ipf_timestamp, strftime_format)
                event_kwargs = dict(
                    data=json.dumps(enriched, ensure_ascii=False, default=str),
                    index=index,
                    sourcetype=sourcetype,
                )
                if event_time is not None:
                    event_kwargs["time"] = event_time
                event_writer.write_event(smi.Event(**event_kwargs))

            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                len(data),
                index,
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "ipf ingestion error", msg_before="Exception raised while ingesting data for ipf_input: ")