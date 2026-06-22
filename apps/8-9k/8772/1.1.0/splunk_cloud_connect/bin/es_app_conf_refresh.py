#!/usr/bin/env python3
# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.
"""
Refresh ES product activation when Enterprise Security default/app.conf changes.

The modular input runs periodically, watches the installed Enterprise Security
app.conf hash, and replays the same Commerce product activation payload used by
initial activation when the hash is missing or changed.
"""

import http.client
import logging
import sys
from typing import Any, Dict, List, Optional

from cloud_product_service import CloudProductService
from constants import (
    APP_NAME,
    CLOUD_PRODUCT_STATUS_ACTIVATED,
    CONFIG_CONF_NAME,
    CONNECTION_STATE_ENABLED,
    ES_PRODUCT_ESSENTIALS,
    ES_PRODUCT_LEGACY,
    ES_PRODUCT_NAMES,
    ES_PRODUCT_PREMIER,
    GENERAL_CONNECTION_STATE_KEY,
    OPERATION_ES_APP_CONF_REFRESH,
    PRODUCT_APP_CONF_HASH_KEY,
    PRODUCT_STANZA_PREFIX,
)
from utils.es_app_conf import compute_es_app_conf_hash
from utils.scs_utils import SCSUtils
from utils.utils import (
    CloudConnectionConfigNotFoundError,
    create_admin_bulletin_error,
    get_cloud_connection_config,
    get_product_config,
    get_splunk_user_for_audit,
    should_run_modinput,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("es_app_conf_refresh")


def _get_active_es_products(product_configs: Dict[str, dict]) -> Dict[str, dict]:
    """Return activated ES edition product stanzas keyed by product name."""
    active_products = {}
    for product_name in ES_PRODUCT_NAMES:
        product_config = product_configs.get(product_name)
        if not product_config:
            continue

        if product_config.get("status") != CLOUD_PRODUCT_STATUS_ACTIVATED:
            logger.info(
                "Skipping ES product with non-activated status: product=%s status=%s",
                product_name,
                product_config.get("status"),
            )
            continue

        active_products[product_name] = product_config

    return active_products


def _select_refresh_product(active_products: Dict[str, dict]) -> Optional[str]:
    """Choose the ES product Commerce should refresh, preferring the highest edition."""
    if ES_PRODUCT_PREMIER in active_products:
        return ES_PRODUCT_PREMIER
    if ES_PRODUCT_ESSENTIALS in active_products:
        return ES_PRODUCT_ESSENTIALS
    if ES_PRODUCT_LEGACY in active_products:
        return ES_PRODUCT_LEGACY
    return None


def _needs_refresh(active_products: Dict[str, dict], current_hash: str) -> bool:
    """Return True when any active ES product has a missing or stale hash."""
    for product_name, product_config in active_products.items():
        stored_hash = product_config.get(PRODUCT_APP_CONF_HASH_KEY)
        if stored_hash != current_hash:
            logger.info(
                "ES app.conf refresh required: product=%s stored_hash_present=%s",
                product_name,
                bool(stored_hash),
            )
            return True
    return False


def _discover_activation_payload(
    service: CloudProductService,
    session_key: str,
    product_name: str,
) -> Optional[Dict[str, Any]]:
    """Find the current activation payload for *product_name* from installed licenses."""
    statuses = service._get_discovery_statuses(session_key)
    discovered = service._scan_discoverable_licenses(statuses)

    for item in discovered:
        if item.get("cloud_product_name") == product_name:
            return item

    service._add_special_server_info_product(discovered, session_key, statuses)

    for item in discovered:
        if item.get("cloud_product_name") == product_name:
            return item

    logger.error(
        "No discoverable activation payload found for ES product: %s",
        product_name,
    )
    return None


def _update_product_app_conf_hash(
    session_key: str,
    product_name: str,
    app_conf_hash: str,
) -> None:
    """Write the ES app.conf hash to one product stanza."""
    stanza_name = f"{PRODUCT_STANZA_PREFIX}{product_name}"
    path = (
        f"/servicesNS/nobody/{APP_NAME}/properties/"
        f"{CONFIG_CONF_NAME}/{stanza_name}/{PRODUCT_APP_CONF_HASH_KEY}"
    )
    resp, _ = SCSUtils.simple_request_with_retry(
        logger=logger,
        method="POST",
        path=path,
        session_key=session_key,
        postargs={"value": app_conf_hash},
    )
    status = getattr(resp, "status", None)
    if status != http.client.OK:
        raise RuntimeError(
            "Failed to update %s for product %s: status=%s"
            % (PRODUCT_APP_CONF_HASH_KEY, product_name, status)
        )


def _stamp_active_es_products(
    session_key: str,
    product_names: List[str],
    app_conf_hash: str,
) -> None:
    """Persist the current ES app.conf hash to all active ES product stanzas."""
    for product_name in product_names:
        _update_product_app_conf_hash(session_key, product_name, app_conf_hash)
        logger.info(
            "Updated ES app.conf hash for product stanza: %s",
            product_name,
        )


def refresh_es_app_conf_activation(session_key: str) -> bool:
    """Run one ES app.conf refresh cycle."""
    logger.info("Starting %s", OPERATION_ES_APP_CONF_REFRESH)

    product_configs = get_product_config(session_key, logger)
    active_products = _get_active_es_products(product_configs)
    if not active_products:
        logger.info("No activated ES edition product stanzas found; skipping")
        return True

    current_hash = compute_es_app_conf_hash(logger)
    if not current_hash:
        logger.error("Unable to compute Enterprise Security app.conf hash")
        return False

    if not _needs_refresh(active_products, current_hash):
        logger.info("ES app.conf hash unchanged for active ES product stanzas")
        return True

    product_to_refresh = _select_refresh_product(active_products)
    if not product_to_refresh:
        logger.info("No ES product selected for refresh; skipping")
        return True

    service = CloudProductService()
    payload = _discover_activation_payload(service, session_key, product_to_refresh)
    if payload is None:
        return False

    user = get_splunk_user_for_audit(
        session_key,
        logger,
        default_user="es_app_conf_refresh",
    )
    license_xml = payload.get("license_xml")
    if not license_xml:
        logger.error(
            "Discovered activation payload is missing license_xml: product=%s",
            product_to_refresh,
        )
        return False

    refreshed = service.refresh_cloud_product_activation(
        session_key=session_key,
        user=user,
        cloud_product_name=product_to_refresh,
        license_xml=license_xml,
        add_ons=payload.get("add_ons") or {},
    )
    if not refreshed:
        logger.error(
            "Commerce ES product activation refresh failed: product=%s",
            product_to_refresh,
        )
        return False

    try:
        _stamp_active_es_products(
            session_key,
            list(active_products.keys()),
            current_hash,
        )
    except Exception as e:
        logger.error(
            "Failed to persist ES app.conf hash after Commerce refresh: %s",
            e,
            exc_info=True,
        )
        return False

    logger.info(
        "Commerce ES product activation refresh completed: product=%s",
        product_to_refresh,
    )
    return True


if __name__ == "__main__":
    session_key = sys.stdin.read().strip()

    if not should_run_modinput(session_key, logger):
        logger.info(
            "Instance is not an SHC captain or has not been elected yet, skipping ES app.conf refresh"
        )
        sys.exit(0)

    try:
        config = get_cloud_connection_config(session_key, logger)
    except (CloudConnectionConfigNotFoundError, ValueError) as e:
        logger.warning("Configuration not found or invalid: %s", e)
        logger.info("Skipping ES app.conf refresh - configuration may not be initialized yet")
        sys.exit(0)

    if config.get(GENERAL_CONNECTION_STATE_KEY) != CONNECTION_STATE_ENABLED:
        logger.info("Connection is not enabled, skipping ES app.conf refresh")
        sys.exit(0)

    success = refresh_es_app_conf_activation(session_key)
    if not success:
        create_admin_bulletin_error(
            session_key,
            logger,
            "es_app_conf_refresh_failure",
            "Enterprise Security activation refresh failed. Please check logs for details.",
        )
        sys.exit(1)

    sys.exit(0)
