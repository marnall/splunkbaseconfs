#!/usr/bin/env python3
# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.
"""
Script for handling periodic key rotation based on configured interval.
"""

import sys
import logging
import http.client
from datetime import datetime, timezone
from utils.secret_manager import SecretManager
from utils.scs_utils import SCSUtils
from utils.utils import (
    should_run_modinput,
    get_cloud_connection_config,
    get_product_config,
    get_product_family,
    create_admin_bulletin_error,
    CloudConnectionConfigNotFoundError,
    get_splunk_user_for_audit,
)
from utils.access_token_helper import (
    get_valid_access_token,
    generate_and_store_access_token,
)
from utils.event_tracker import track_scs_operation
from constants import (
    APP_NAME,
    AUDIT_EVENT_KEY_ROTATION_KEYS_RETRIEVED,
    AUDIT_EVENT_KEY_ROTATION_KEY_RETRIEVAL_FAILED,
    AUDIT_EVENT_KEY_ROTATION_KEY_ADDED,
    AUDIT_EVENT_KEY_ROTATION_KEY_ADD_FAILED,
    AUDIT_EVENT_KEY_ROTATION_KEY_DELETED,
    AUDIT_EVENT_KEY_ROTATION_KEY_DELETE_FAILED,
    CONFIG_CONF_NAME,
    CONFIG_STANZA,
    PRODUCT_STANZA_PREFIX,
    LAST_ROTATION_TIMESTAMP_KEY,
    DEFAULT_ROTATION_INTERVAL_DAYS,
    GENERAL_CONNECTION_STATE_KEY,
    CONNECTION_STATE_ENABLED,
    CLOUD_PRODUCT_STATUS_ACTIVATED,
    PRODUCT_STATUS_KEY,
    KEY_ROTATION_OPERATION,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("key_rotation")


def _validate_rotation_config(configs: dict):
    if not configs.get("spID"):
        raise ValueError("spID not found in cloud-connection.conf")

    if not configs.get("tenantName"):
        raise ValueError("tenantName not found in cloud-connection.conf")

    if not configs.get("regionAuthHostname"):
        raise ValueError("regionAuthHostname not found in cloud-connection.conf")


def update_config_value(
    session_key: str, key: str, value: str, stanza: str = CONFIG_STANZA
):
    path = f"/servicesNS/nobody/{APP_NAME}/properties/{CONFIG_CONF_NAME}/{stanza}/{key}"
    resp, content = SCSUtils.simple_request_with_retry(
        logger=logger,
        method="POST",
        path=path,
        session_key=session_key,
        postargs={"value": value},
    )

    status = getattr(resp, "status", None)
    if status != http.client.OK:
        logger.error(
            "Failed to update config key %s in stanza %s, status=%s",
            key,
            stanza,
            status,
        )
        raise RuntimeError(
            "Failed to update config key %s in stanza %s" % (key, stanza)
        )

    logger.info("Successfully updated %s in %s", key, stanza)


def check_if_rotation_needed(last_rotation_timestamp, rotation_interval_days) -> bool:
    if not last_rotation_timestamp:
        logger.info("Rotation needed: No previous rotation found")
        return True

    try:
        last_rotation_ts = int(last_rotation_timestamp)
        last_rotation = datetime.fromtimestamp(last_rotation_ts, tz=timezone.utc)
        now = datetime.now(timezone.utc)

        days_since_rotation = (now - last_rotation).days

        # Format timestamp for logging
        last_rotation_str = last_rotation.strftime("%Y-%m-%d %H:%M:%S UTC")

        if days_since_rotation >= rotation_interval_days:
            logger.info(
                "Rotation needed: %s days since last rotation on %s "
                "(rotation interval of %s days reached)",
                days_since_rotation,
                last_rotation_str,
                rotation_interval_days,
            )
            return True
        else:
            days_until_rotation = rotation_interval_days - days_since_rotation
            logger.info(
                "Rotation not needed: %s days since last rotation on %s "
                "(rotation in %s days)",
                days_since_rotation,
                last_rotation_str,
                days_until_rotation,
            )
            return False

    except ValueError as e:
        logger.error("Invalid timestamp format, forcing rotation: %s", e)
        return True


def _get_current_key_and_kid(
    session_key: str, secret_manager: SecretManager, realm: str
):
    current_key_and_kid = secret_manager.get_private_key_and_kid(session_key, realm)
    if not current_key_and_kid:
        raise RuntimeError("No existing key found in secret storage")

    private_key, kid = current_key_and_kid
    logger.info("Retrieved private key and kid from secret storage")
    return private_key, kid


def _rotate_single_sp(
    session_key: str,
    principal_id: str,
    tenant_name: str,
    secret_manager: SecretManager,
    realm: str,
    stanza_name: str,
) -> bool:
    try:
        current_private_key, current_kid = _get_current_key_and_kid(
            session_key, secret_manager, realm
        )
        # Use the SP's principal_id as the kid prefix (not the issuer ID) so
        # that each SP on the same SHU has a distinct kid and the "already current"
        # check below works correctly across multiple SPs.
        new_kid = SCSUtils.build_kid_from_issuer_id(principal_id)

        if current_kid == new_kid:
            logger.info(
                "Current key (%s) is already the key for today, skipping rotation",
                current_kid,
            )
            return True

        splunk_user = get_splunk_user_for_audit(
            session_key, logger, default_user="key_rotation_script"
        )

        sp_access_token, _ = get_valid_access_token(
            session_key=session_key,
            realm=realm,
            principal_id=principal_id,
            tenant_name=tenant_name,
            logger=logger,
        )

        # Retrieve existing public key IDs from SCS
        with track_scs_operation(
            session_key,
            logger,
            operation=KEY_ROTATION_OPERATION,
            event_type_ok=AUDIT_EVENT_KEY_ROTATION_KEYS_RETRIEVED,
            event_type_failed=AUDIT_EVENT_KEY_ROTATION_KEY_RETRIEVAL_FAILED,
        ):
            existing_key_ids = SCSUtils.retrieve_principal_public_key_ids(
                logger=logger,
                session_key=session_key,
                splunk_user=splunk_user,
                access_token=sp_access_token,
                principal_id=principal_id,
                tenant_name=tenant_name,
            )
        logger.info(
            "Retrieved %s existing public key IDs from SCS", len(existing_key_ids)
        )

        if new_kid in existing_key_ids:
            logger.info(
                "Key for today (%s) already exists in SCS, skipping rotation", new_kid
            )
            return True

        # Clean up extra key if it's not current key retrieved from secret storage
        if len(existing_key_ids) >= 2:
            logger.warning(
                "Found %s keys in SCS, cleaning up extra keys", len(existing_key_ids)
            )
            for key_id in existing_key_ids:
                if key_id != current_kid:
                    logger.info("Deleting extra key from SCS: %s", key_id)
                    with track_scs_operation(
                        session_key,
                        logger,
                        operation=KEY_ROTATION_OPERATION,
                        event_type_ok=AUDIT_EVENT_KEY_ROTATION_KEY_DELETED,
                        event_type_failed=AUDIT_EVENT_KEY_ROTATION_KEY_DELETE_FAILED,
                    ):
                        SCSUtils.delete_public_key(
                            logger=logger,
                            session_key=session_key,
                            splunk_user=splunk_user,
                            access_token=sp_access_token,
                            principal_id=principal_id,
                            public_key_id=key_id,
                            tenant_name=tenant_name,
                        )
                    logger.info("Successfully deleted extra key: %s", key_id)

        new_private_key = SCSUtils.generate_ecdsa_private_key(logger)
        new_public_key = SCSUtils.derive_ecdsa_public_key(logger, new_private_key)

        with track_scs_operation(
            session_key,
            logger,
            operation=KEY_ROTATION_OPERATION,
            event_type_ok=AUDIT_EVENT_KEY_ROTATION_KEY_ADDED,
            event_type_failed=AUDIT_EVENT_KEY_ROTATION_KEY_ADD_FAILED,
        ):
            SCSUtils.add_public_key_to_principal(
                logger=logger,
                session_key=session_key,
                splunk_user=splunk_user,
                access_token=sp_access_token,
                principal_id=principal_id,
                kid=new_kid,
                public_key=new_public_key,
                tenant_name=tenant_name,
            )
        logger.info("Successfully added new public key (%s) to principal", new_kid)

        secret_manager.upsert_private_key_and_kid(
            session_key, realm, new_private_key, new_kid
        )
        logger.info("Successfully stored new private key and kid")

        new_sp_access_token = generate_and_store_access_token(
            session_key=session_key,
            secret_manager=secret_manager,
            realm=realm,
            kid=new_kid,
            private_key=new_private_key,
            principal_id=principal_id,
            tenant_name=tenant_name,
            splunk_user=splunk_user,
            logger=logger,
        )

        rotation_timestamp = int(datetime.now(timezone.utc).timestamp())
        update_config_value(
            session_key,
            LAST_ROTATION_TIMESTAMP_KEY,
            str(rotation_timestamp),
            stanza=stanza_name,
        )

        # Delete the old key from SCS (cleanup operation, should not fail rotation)
        logger.info("Deleting old key (%s) from SCS", current_kid)
        try:
            with track_scs_operation(
                session_key,
                logger,
                operation=KEY_ROTATION_OPERATION,
                event_type_ok=AUDIT_EVENT_KEY_ROTATION_KEY_DELETED,
                event_type_failed=AUDIT_EVENT_KEY_ROTATION_KEY_DELETE_FAILED,
            ):
                SCSUtils.delete_public_key(
                    logger=logger,
                    session_key=session_key,
                    splunk_user=splunk_user,
                    access_token=new_sp_access_token,
                    principal_id=principal_id,
                    public_key_id=current_kid,
                    tenant_name=tenant_name,
                )
            logger.info("Successfully deleted old key (%s)", current_kid)
        except Exception as e:
            logger.error(
                "Failed to delete old key %s: %s", current_kid, e, exc_info=True
            )

        return True

    except RuntimeError as e:
        logger.error("Key rotation failed: %s", e)
    except Exception as e:
        logger.error("Unexpected error during key rotation: %s", e, exc_info=True)

    return False


def _rotate_bootstrap_sp(
    session_key: str, config: dict, secret_manager: SecretManager
) -> bool:
    principal_id = config["spID"]
    tenant_name = config["tenantName"]

    logger.info("===== Rotating key for bootstrapping SP =====")
    return _rotate_single_sp(
        session_key=session_key,
        principal_id=principal_id,
        tenant_name=tenant_name,
        secret_manager=secret_manager,
        realm=APP_NAME,
        stanza_name=CONFIG_STANZA,
    )


def _rotate_product_sp(
    session_key: str,
    product_name: str,
    product_config: dict,
    general_config: dict,
    secret_manager: SecretManager,
) -> bool:
    principal_id = product_config.get("spID")

    if not principal_id:
        logger.error("Product %s missing spID", product_name)
        return False

    tenant_name = general_config["tenantName"]
    stanza_name = f"{PRODUCT_STANZA_PREFIX}{product_name}"
    keypair_realm = get_product_family(product_name)
    if keypair_realm is None:
        logger.warning(
            "Skipping key rotation for unknown cloud product: %s", product_name
        )
        return False

    logger.info(
        "===== Rotating key for %s SP (keypair_realm=%s) =====",
        product_name,
        keypair_realm,
    )
    return _rotate_single_sp(
        session_key=session_key,
        principal_id=principal_id,
        tenant_name=tenant_name,
        secret_manager=secret_manager,
        realm=keypair_realm,
        stanza_name=stanza_name,
    )


def perform_key_rotation(
    session_key: str, general_config: dict, rotation_interval_days: int
) -> bool:
    overall_success = True
    secret_manager = SecretManager(logger)

    # 1. Bootstrapping SP's keys
    try:
        bootstrap_last_rotation = general_config.get(LAST_ROTATION_TIMESTAMP_KEY)
        if check_if_rotation_needed(bootstrap_last_rotation, rotation_interval_days):
            bootstrap_success = _rotate_bootstrap_sp(
                session_key, general_config, secret_manager
            )
            if bootstrap_success:
                logger.info("Key rotation completed successfully for bootstrapping SP")
            else:
                logger.error("Key rotation failed for bootstrapping SP")
                overall_success = False
        else:
            logger.info("Key rotation not needed for bootstrapping SP")
    except Exception as e:
        logger.error("Unexpected error during key rotation: %s", e, exc_info=True)
        overall_success = False

    # 2. Product SP's keys
    product_stanzas = get_product_config(session_key, logger)

    if not product_stanzas:
        logger.info("No product stanzas found")

    # Group activated products by keypair family — siblings share a keypair so we
    # rotate once per family rather than once per product.
    families: dict = {}  # realm -> list of (product_name, product_config)
    for product_name, product_config in product_stanzas.items():
        product_status = product_config.get(PRODUCT_STATUS_KEY)
        if product_status != CLOUD_PRODUCT_STATUS_ACTIVATED:
            logger.debug(
                "Skipping key rotation for product %s (status=%s)",
                product_name,
                product_status,
            )
            continue
        realm = get_product_family(product_name)
        if realm is None:
            logger.warning(
                "Skipping key rotation for unknown cloud product: %s", product_name
            )
            continue
        families.setdefault(realm, []).append((product_name, product_config))

    for realm, members in families.items():
        # Use the first member as the representative for the actual SCS rotation.
        representative_name, representative_config = members[0]
        siblings = [name for name, _ in members[1:]]
        if siblings:
            logger.info(
                "Family %s: rotating via %s, siblings: %s",
                realm,
                representative_name,
                siblings,
            )

        try:
            product_last_rotation = representative_config.get(
                LAST_ROTATION_TIMESTAMP_KEY
            )
            if check_if_rotation_needed(product_last_rotation, rotation_interval_days):
                product_success = _rotate_product_sp(
                    session_key,
                    representative_name,
                    representative_config,
                    general_config,
                    secret_manager,
                )
                if product_success:
                    logger.info(
                        "Key rotation completed successfully for product: %s",
                        representative_name,
                    )
                    # Stamp siblings so they don't trigger a spurious rotation next cycle.
                    rotation_timestamp = str(
                        int(datetime.now(timezone.utc).timestamp())
                    )
                    for sibling_name in siblings:
                        try:
                            update_config_value(
                                session_key,
                                LAST_ROTATION_TIMESTAMP_KEY,
                                rotation_timestamp,
                                stanza=f"{PRODUCT_STANZA_PREFIX}{sibling_name}",
                            )
                            logger.info(
                                "Updated rotation timestamp for sibling product: %s",
                                sibling_name,
                            )
                        except Exception as e:
                            logger.error(
                                "Failed to update rotation timestamp for sibling %s: %s",
                                sibling_name,
                                e,
                            )
                else:
                    logger.error(
                        "Key rotation failed for product: %s", representative_name
                    )
                    overall_success = False
            else:
                logger.info(
                    "Key rotation not needed for product: %s", representative_name
                )
        except Exception as e:
            logger.error(
                "Unexpected error during product %s key rotation: %s",
                representative_name,
                e,
                exc_info=True,
            )
            overall_success = False

    return overall_success


if __name__ == "__main__":
    # Read session key from stdin (passed by Splunk)
    session_key = sys.stdin.read().strip()

    if not should_run_modinput(session_key, logger):
        logger.info(
            "Instance is not an SHC captain or has not been elected yet, skipping key rotation"
        )
        sys.exit(0)

    # Load configuration
    try:
        configs = get_cloud_connection_config(session_key, logger)
    except CloudConnectionConfigNotFoundError as e:
        logger.error("Configuration error: %s", e)
        create_admin_bulletin_error(
            session_key,
            logger,
            "key_rotation_failure",
            f"Key rotation configuration error: {e}. Please configure spID, tenantName, and regionAuthHostname in cloud-connection.conf.",
        )
        sys.exit(1)

    if configs.get(GENERAL_CONNECTION_STATE_KEY) != CONNECTION_STATE_ENABLED:
        logger.info("Connection is not enabled, skipping key rotation")
        sys.exit(0)

    # Validate configuration only if connection is enabled
    try:
        _validate_rotation_config(configs)
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        create_admin_bulletin_error(
            session_key,
            logger,
            "key_rotation_failure",
            f"Key rotation configuration error: {e}. Please configure spID, tenantName, and regionAuthHostname in cloud-connection.conf.",
        )
        sys.exit(1)

    # Get rotation interval with default
    rotation_interval_str = configs.get("rotationInterval")
    if rotation_interval_str:
        try:
            rotation_interval_days = int(rotation_interval_str)
        except ValueError:
            logger.warning(
                "Invalid rotationInterval %s, using default %s days",
                rotation_interval_str,
                DEFAULT_ROTATION_INTERVAL_DAYS,
            )
            rotation_interval_days = DEFAULT_ROTATION_INTERVAL_DAYS
    else:
        rotation_interval_days = DEFAULT_ROTATION_INTERVAL_DAYS

    # Perform key rotation for bootstrap and all product SPs
    success = perform_key_rotation(session_key, configs, rotation_interval_days)

    if not success:
        logger.error("Key rotation failed")
        create_admin_bulletin_error(
            session_key,
            logger,
            "key_rotation_failure",
            "Key rotation failed. Please check logs for details and ensure the principal configuration is correct.",
        )
        sys.exit(1)

    sys.exit(0)
