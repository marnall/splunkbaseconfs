#!/usr/bin/env python3
# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.
"""
Script for periodic access token refresh.

This modular input runs every 5 minutes and refreshes access tokens
that are about to expire (within 25 minutes). It handles both the
bootstrap SP and all product SPs.

This uses a proactive refresh buffer (25 min) as the primary token refresh
mechanism.
"""

import socket
import sys
import logging

from utils.access_token_helper import get_valid_access_token
from utils.scs_utils import SCSUtils
from utils.cloud_connection_event_log import CloudConnectionEventLog
from utils.utils import (
    should_run_modinput,
    get_cloud_connection_config,
    get_product_config,
    get_product_family,
    create_admin_bulletin_error,
    CloudConnectionConfigNotFoundError,
)
from constants import (
    AUDIT_EVENT_TOKEN_REFRESH_OK,
    AUDIT_EVENT_TOKEN_REFRESH_FAILED,
    AUDIT_SEVERITY_INFO,
    AUDIT_SEVERITY_ERROR,
    MODINPUT_TOKEN_EXPIRY_BUFFER_MINUTES,
    APP_NAME,
    GENERAL_CONNECTION_STATE_KEY,
    CONNECTION_STATE_ENABLED,
    CLOUD_PRODUCT_STATUS_ACTIVATED,
    OPERATION_TOKEN_REFRESH,
    PRODUCT_STATUS_KEY,
    SP_PRODUCT_NAME_BOOTSTRAP,
    SP_TYPE_BOOTSTRAP,
    SP_TYPE_PRODUCT,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("access_token_refresh")


def _resolve_local_hostname(session_key: str) -> str:
    """Return the Splunk serverName, falling back to socket.gethostname() on error."""
    try:
        return SCSUtils.get_server_name(logger, session_key)
    except Exception:
        return socket.gethostname()


def _refresh_bootstrap_sp_token_if_needed(session_key: str, config: dict) -> bool:
    """
    Refresh access token for the bootstrap SP if needed.
    Checks if the token is still valid and only refreshes if expiring soon.
    """
    principal_id = config["spID"]
    tenant_name = config["tenantName"]
    local_hostname = _resolve_local_hostname(session_key)
    try:
        logger.info("===== Checking bootstrap SP token =====")

        _, refreshed = get_valid_access_token(
            session_key=session_key,
            realm=APP_NAME,
            principal_id=principal_id,
            tenant_name=tenant_name,
            logger=logger,
            buffer_minutes=MODINPUT_TOKEN_EXPIRY_BUFFER_MINUTES,
        )

        if refreshed:
            CloudConnectionEventLog(session_key, logger).log(
                operation=OPERATION_TOKEN_REFRESH,
                event_type=AUDIT_EVENT_TOKEN_REFRESH_OK,
                severity=AUDIT_SEVERITY_INFO,
                details={
                    "sp_id": config.get("spID", ""),
                    "sp_type": SP_TYPE_BOOTSTRAP,
                    "product_name": SP_PRODUCT_NAME_BOOTSTRAP,
                    "local_hostname": local_hostname,
                    "scs_hostname": config.get("regionAuthHostname", ""),
                },
            )
        return True

    except Exception as e:
        logger.error("Failed to get bootstrap SP token: %s", e, exc_info=True)
        CloudConnectionEventLog(session_key, logger).log(
            operation=OPERATION_TOKEN_REFRESH,
            event_type=AUDIT_EVENT_TOKEN_REFRESH_FAILED,
            severity=AUDIT_SEVERITY_ERROR,
            details={
                "sp_id": config.get("spID", ""),
                "sp_type": SP_TYPE_BOOTSTRAP,
                "product_name": SP_PRODUCT_NAME_BOOTSTRAP,
                "local_hostname": local_hostname,
                "scs_hostname": config.get("regionAuthHostname", ""),
            },
        )
        return False


def _refresh_product_sp_token_if_needed(
    session_key: str, product_name: str, product_config: dict, general_config: dict
) -> bool:
    """
    Refresh access token for a product SP if needed.
    Checks if the token is still valid and only refreshes if expiring soon.
    """
    principal_id = product_config.get("spID")
    tenant_name = general_config["tenantName"]
    local_hostname = _resolve_local_hostname(session_key)
    try:
        if not principal_id:
            logger.error("Product %s missing spID", product_name)
            CloudConnectionEventLog(session_key, logger).log(
                operation=OPERATION_TOKEN_REFRESH,
                event_type=AUDIT_EVENT_TOKEN_REFRESH_FAILED,
                severity=AUDIT_SEVERITY_ERROR,
                details={
                    "sp_id": "",
                    "sp_type": SP_TYPE_PRODUCT,
                    "product_name": product_name,
                    "local_hostname": local_hostname,
                    "scs_hostname": general_config.get("regionAuthHostname", ""),
                },
            )
            return False

        logger.info("===== Checking %s SP token =====", product_name)
        family = get_product_family(product_name)
        if family is None:
            logger.warning(
                "Skipping token refresh for unknown cloud product: %s", product_name
            )
            return False

        _, refreshed = get_valid_access_token(
            session_key=session_key,
            realm=family,
            principal_id=principal_id,
            tenant_name=tenant_name,
            logger=logger,
            buffer_minutes=MODINPUT_TOKEN_EXPIRY_BUFFER_MINUTES,
        )

        if refreshed:
            CloudConnectionEventLog(session_key, logger).log(
                operation=OPERATION_TOKEN_REFRESH,
                event_type=AUDIT_EVENT_TOKEN_REFRESH_OK,
                severity=AUDIT_SEVERITY_INFO,
                details={
                    "sp_id": product_config.get("spID", ""),
                    "sp_type": SP_TYPE_PRODUCT,
                    "product_name": product_name,
                    "local_hostname": local_hostname,
                    "scs_hostname": general_config.get("regionAuthHostname", ""),
                },
            )
        return True

    except Exception as e:
        logger.error(
            "Failed to get product %s token: %s", product_name, e, exc_info=True
        )
        CloudConnectionEventLog(session_key, logger).log(
            operation=OPERATION_TOKEN_REFRESH,
            event_type=AUDIT_EVENT_TOKEN_REFRESH_FAILED,
            severity=AUDIT_SEVERITY_ERROR,
            details={
                "sp_id": product_config.get("spID", ""),
                "sp_type": SP_TYPE_PRODUCT,
                "product_name": product_name,
                "local_hostname": local_hostname,
                "scs_hostname": general_config.get("regionAuthHostname", ""),
            },
        )
        return False


def perform_token_refresh(session_key: str, general_config: dict) -> bool:
    """
    Refresh access tokens for bootstrap SP and all product SPs if needed.
    """
    overall_success = True

    # 1. Refresh bootstrap SP token
    try:
        success = _refresh_bootstrap_sp_token_if_needed(session_key, general_config)
        if not success:
            overall_success = False
    except Exception as e:
        overall_success = False
        logger.error(
            "Unexpected error refreshing bootstrap SP token: %s", e, exc_info=True
        )

    # 2. Refresh product SP tokens — once per family since siblings share a token realm.
    product_stanzas = get_product_config(session_key, logger)

    seen_families: set = set()
    for product_name, product_config in product_stanzas.items():
        product_status = product_config.get(PRODUCT_STATUS_KEY)
        if product_status != CLOUD_PRODUCT_STATUS_ACTIVATED:
            logger.debug(
                "Skipping token refresh for product %s (status=%s)",
                product_name,
                product_status,
            )
            continue

        family = get_product_family(product_name)
        if family is None:
            logger.warning(
                "Skipping token refresh for unknown cloud product: %s", product_name
            )
            continue
        if family in seen_families:
            logger.debug(
                "Skipping token refresh for product %s — family %s already refreshed",
                product_name,
                family,
            )
            continue
        seen_families.add(family)

        try:
            success = _refresh_product_sp_token_if_needed(
                session_key, product_name, product_config, general_config
            )
            if not success:
                overall_success = False
        except Exception as e:
            overall_success = False
            logger.error(
                "Unexpected error refreshing product %s token: %s",
                product_name,
                e,
                exc_info=True,
            )

    return overall_success


if __name__ == "__main__":
    # Read session key from stdin (passed by Splunk)
    session_key = sys.stdin.read().strip()

    if not should_run_modinput(session_key, logger):
        logger.info(
            "Instance is not an SHC captain or has not been elected yet, skipping token refresh"
        )
        sys.exit(0)

    # Load configuration
    try:
        configs = get_cloud_connection_config(session_key, logger)
    except (CloudConnectionConfigNotFoundError, ValueError) as e:
        logger.warning("Configuration not found or invalid: %s", e)
        logger.info("Skipping token refresh - configuration may not be initialized yet")
        sys.exit(0)

    if configs.get(GENERAL_CONNECTION_STATE_KEY) != CONNECTION_STATE_ENABLED:
        logger.info("Connection is not enabled, skipping token refresh")
        sys.exit(0)

    # Validate required configuration
    if (
        not configs.get("spID")
        or not configs.get("tenantName")
        or not configs.get("regionAuthHostname")
    ):
        logger.warning(
            "Missing required configuration (spID, tenantName, or regionAuthHostname), skipping token refresh"
        )
        sys.exit(0)

    # Perform token refresh
    success = perform_token_refresh(session_key, configs)

    if not success:
        logger.error("Access token refresh failed")
        create_admin_bulletin_error(
            session_key,
            logger,
            "access_token_refresh_failure",
            "Access token refresh failed. Please check logs for details.",
        )
        sys.exit(1)

    sys.exit(0)
