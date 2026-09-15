"""Parses and validates all ingestion configuration from Splunk storage passwords."""

import flare_constants as const
import json
import logging
import urllib.parse

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Optional


logger = logging.getLogger("flare_cron_job")


def get_proxy_settings(config: dict) -> Optional[dict]:
    """Parse proxy settings from a storage configuration dictionary."""
    if config.get(const.KEY_PROXY_ENABLED) != "true":
        return None
    proxy_type = config.get(const.KEY_PROXY_TYPE) or "http"
    proxy_host = config.get(const.KEY_PROXY_HOST)
    proxy_port = config.get(const.KEY_PROXY_PORT)
    if not proxy_host or not proxy_port:
        return None

    proxy_username = config.get(const.KEY_PROXY_USERNAME)
    proxy_password = config.get(const.KEY_PROXY_PASSWORD)

    if proxy_username and proxy_password:
        user_enc = urllib.parse.quote_plus(proxy_username)
        pass_enc = urllib.parse.quote_plus(proxy_password)
        proxy_uri = f"{proxy_type}://{user_enc}:{pass_enc}@{proxy_host}:{proxy_port}"
    else:
        proxy_uri = f"{proxy_type}://{proxy_host}:{proxy_port}"

    return {"http": proxy_uri, "https": proxy_uri}


def parse_ingestion_config(config: dict) -> Optional[dict]:
    """
    Parse all ingestion settings from the raw Splunk storage config dict.
    Returns a structured dict with all values parsed and validated,
    or None if a critical field (api_key, tenant_ids) is missing.
    """

    #  Critical: API Key
    api_key = config.get(const.KEY_API_KEY)
    if not api_key:
        logger.warning(
            "Configuration has been removed or API key is missing. "
            "Data ingestion is stopped."
        )
        return None

    #  Critical: Tenant IDs
    tenant_ids: list = []
    tenant_ids_str = config.get(const.KEY_TENANT_IDS)
    if tenant_ids_str:
        try:
            tenant_ids = json.loads(tenant_ids_str)
        except Exception:
            logger.warning("We had trouble reading the Tenant IDs from the config.")

    if not tenant_ids:
        logger.error(
            "No Tenant IDs were found. We don't know which environments "
            "to fetch data for."
        )
        return None

    #  Optional: Tenant Names Map
    tenant_names_map: dict = {}
    tenant_names_raw = config.get(const.KEY_TENANT_NAMES)
    if tenant_names_raw:
        try:
            tenant_names_map = json.loads(tenant_names_raw)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to parse tenant_names from storage: %s", e)

    #  Filters
    ingest_full_event_data = config.get(const.KEY_INGEST_FULL_EVENT_DATA) == "true"

    severities_filter_str = config.get(const.KEY_SEVERITIES_FILTER)
    severities_filter = (
        severities_filter_str.split(",") if severities_filter_str else []
    )

    source_types_filter_str = config.get(const.KEY_SOURCE_TYPES_FILTER)
    source_types_filter = (
        source_types_filter_str.split(",") if source_types_filter_str else []
    )

    #  Backfill
    backfill_days_str = config.get(const.KEY_BACKFILL_DAYS)
    try:
        backfill_days = (
            int(backfill_days_str) if backfill_days_str else const.DEFAULT_BACKFILL_DAYS
        )
    except ValueError:
        logger.warning(
            "The backfill setting seems invalid ('%s'), defaulting to %d.",
            backfill_days_str,
            const.DEFAULT_BACKFILL_DAYS,
        )
        backfill_days = const.DEFAULT_BACKFILL_DAYS

    backfill_start_date = (
        (datetime.now(timezone.utc) - timedelta(days=backfill_days))
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    #  Network
    proxies = get_proxy_settings(config)

    ssl_verify_val = config.get(const.KEY_SSL_VERIFY)
    ssl_verify = (
        ssl_verify_val.lower() == "true" if ssl_verify_val is not None else True
    )

    #  Index
    index_name = config.get(const.KEY_INDEX_NAME)

    #  Logging
    log_level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    log_level_str = (config.get(const.KEY_LOG_LEVEL) or "INFO").upper()
    log_level = log_level_map.get(log_level_str, logging.INFO)

    # Apply dynamic log level immediately so the summary log respects it
    logger.setLevel(log_level)
    for handler in logger.handlers:
        handler.setLevel(log_level)

    #  Summary log
    logger.info(
        "Config valid. %d tenants, %d days backfill. Full detail: %s.%s",
        len(tenant_ids),
        backfill_days,
        ingest_full_event_data,
        " (Proxy on)" if proxies else "",
    )
    return {
        "api_key": api_key,
        "tenant_ids": tenant_ids,
        "tenant_names_map": tenant_names_map,
        "ingest_full_event_data": ingest_full_event_data,
        "severities_filter": severities_filter,
        "source_types_filter": source_types_filter,
        "backfill_days": backfill_days,
        "backfill_start_date": backfill_start_date,
        "proxies": proxies,
        "ssl_verify": ssl_verify,
        "index_name": index_name,
        "log_level": log_level,
    }
