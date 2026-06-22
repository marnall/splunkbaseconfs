#!/usr/bin/env python3
# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.
"""
Cloud Product Service Implementation

This module implements the ServiceProtocol interface for handling
cloud product operations including activation, deactivation, and status retrieval.
"""

import os
import sys

# Add the bin directory to sys.path to ensure correct module imports
bin_dir = os.path.dirname(os.path.abspath(__file__))
if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

import base64
import http.client
import json
import logging
from pathlib import Path
import time
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

from constants import (
    APP_NAME,
    AUDIT_EVENT_PRODUCT_ACTIVATION_SUCCESS,
    AUDIT_EVENT_PRODUCT_ACTIVATION_FAILURE,
    AUDIT_SEVERITY_INFO,
    AUDIT_SEVERITY_ERROR,
    CAPABILITY_EDIT_CLOUD_CONNECTION,
    CAPABILITY_GET_CLOUD_CONNECTION_PRODUCT,
    CLOUD_PRODUCT_METADATA,
    CLOUD_PRODUCT_STATUS_ACTIVATED,
    CLOUD_PRODUCT_STATUS_ACTIVATION_FAILED,
    CLOUD_PRODUCT_STATUS_DEACTIVATED,
    CLOUD_PRODUCT_STATUS_IN_PROGRESS,
    CLOUD_PRODUCT_STATUS_REVERSE_MAPPING,
    CLOUD_PRODUCT_STATUS_UNAVAILABLE,
    CONFIG_STANZA,
    CONNECTION_STATE_ENABLED,
    GENERAL_CONNECTION_STATE_KEY,
    GENERAL_TENANT_NAME_KEY,
    OPERATION_ACTIVATE_CLOUD_PRODUCT,
    PRODUCT_NAME_KEY,
    PRODUCT_PRODUCT_CODE_KEY,
    PRODUCT_SP_ID_KEY,
    PRODUCT_STANZA_PREFIX,
    PRODUCT_LICENSE_GUID_KEY,
    PRODUCT_STATUS_KEY,
    PRODUCT_APP_CONF_HASH_KEY,
    SPLUNK_SERVER_INFO_URI,
    SP_ACCESS_TOKEN_SECRET_NAME,
)
from generated.interface import ServiceProtocol
from generated.models import (
    CloudProductActivated,
    CloudProductActivation,
    CloudProductActivationDiscovery,
    Error,
)
from generated.responses import (
    ActivateCloudProductResponseBuilder,
    DeactivateCloudProductResponseBuilder,
    ListCloudProductActivationsResponseBuilder,
)
from generated.req_resp import Response, SplunkContext
from utils.cloud_connection_event_log import CloudConnectionEventLog
from utils.event_tracker import tracked_request_with_splunkd_proxy
from utils.log import setup_logger
from utils.access_token_helper import generate_and_store_access_token
from utils.scs_utils import SCSUtils
from utils.search_head_unit import SearchHeadUnit
from utils.secret_manager import SecretManager
from utils.es_app_conf import compute_es_app_conf_hash, is_es_edition_product
from utils.utils import (
    CloudConnectionConfigNotFoundError,
    get_cloud_connection_conf_entries,
    get_cloud_connection_config,
    get_product_family,
    has_capability,
    _require_capability,
)
from constants import get_commerce_api_uri_cloud_product

logger = setup_logger("cloud_product_service", level=logging.INFO)

DISCOVERY_STATUSES = frozenset(
    {
        CLOUD_PRODUCT_STATUS_ACTIVATED,
        CLOUD_PRODUCT_STATUS_DEACTIVATED,
        CLOUD_PRODUCT_STATUS_IN_PROGRESS,
        CLOUD_PRODUCT_STATUS_ACTIVATION_FAILED,
        CLOUD_PRODUCT_STATUS_UNAVAILABLE,
    }
)


class CloudProductService(ServiceProtocol):
    """
    Service implementation for Cloud Product API.

    Handles:
    - Retrieving cloud product connection details
    - Activating cloud product connections
    - Deactivating cloud product connections
    """

    def __init__(self):
        """Initialize the cloud product service."""
        self.logger = logger
        self.logger.info("CloudProductService initialized")

    @staticmethod
    def _find_general_and_product_stanzas(entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        stanzas = {}
        for entry in entries:
            stanza_name = entry.get('name')
            if not isinstance(stanza_name, str) or not stanza_name:
                continue
            content = entry.get('content') or {}
            if not isinstance(content, dict):
                continue

            if stanza_name == CONFIG_STANZA or stanza_name.startswith(PRODUCT_STANZA_PREFIX):
                stanzas[stanza_name] = content
        return stanzas

    @staticmethod
    def _normalize_discovery_status(status: Any) -> str:
        if not isinstance(status, str):
            return CLOUD_PRODUCT_STATUS_DEACTIVATED

        normalized_status = status.strip().lower()
        if normalized_status in DISCOVERY_STATUSES:
            return normalized_status

        return CLOUD_PRODUCT_STATUS_DEACTIVATED

    def _get_discovery_statuses(self, session_key: str) -> Dict[str, str]:
        statuses = {}
        entries = get_cloud_connection_conf_entries(
            logger=self.logger,
            session_key=session_key,
        )
        for entry in entries:
            stanza_name = entry.get("name")
            if not isinstance(stanza_name, str) or not stanza_name.startswith(PRODUCT_STANZA_PREFIX):
                continue

            content = entry.get("content") or {}
            if not isinstance(content, dict):
                continue

            cloud_product_name = content.get(PRODUCT_NAME_KEY) or stanza_name[len(PRODUCT_STANZA_PREFIX):]
            if not isinstance(cloud_product_name, str) or not cloud_product_name:
                continue

            statuses[cloud_product_name] = self._normalize_discovery_status(
                content.get(PRODUCT_STATUS_KEY)
            )
        return statuses

    @staticmethod
    def _find_cloud_connected_add_on(payload_root: "Element") -> Optional["Element"]:
        add_ons_root = payload_root.find("add_ons")
        if add_ons_root is None:
            return None

        # we're searching for licenses on the Search Head that are embedded in Splunk Apps
        # by definition they will include only one add_on so we can exit as soon as we get anything
        for add_on in add_ons_root.findall("add_on"):
            for parameter in add_on.findall("parameter"):
                if parameter.get("key") == "cloud_connected" and parameter.get("value") == "1":
                    return add_on
        return None

    def _scan_discoverable_licenses(
        self,
        statuses: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        splunk_home = os.environ.get("SPLUNK_HOME")
        if not splunk_home:
            raise RuntimeError("SPLUNK_HOME is not set")

        root_path = Path(splunk_home, "etc", "apps")
        if not root_path.exists():
            raise RuntimeError(f"SPLUNK_HOME/etc/apps does not exist: {root_path}")

        discovered = []

        for license_path in root_path.rglob("*.lic"):
            try:
                license_xml = license_path.read_text(encoding="utf-8")
                license_root = ET.fromstring(license_xml)
            except (OSError, UnicodeDecodeError, ET.ParseError, DefusedXmlException) as e:
                self.logger.warning("Skipping unreadable license file %s: %s", license_path, e)
                continue

            payload_root = license_root.find("payload")
            if payload_root is None:
                continue

            current_time = time.time()
            creation_time = payload_root.findtext("creation_time")
            if creation_time:
                try:
                    if float(creation_time) > current_time:
                        self.logger.warning(
                            "License creation_time is in the future for %s: %s",
                            license_path,
                            creation_time,
                        )
                except ValueError:
                    self.logger.warning(
                        "License has invalid creation_time in %s: %s",
                        license_path,
                        creation_time,
                    )

            expiration_time = payload_root.findtext("expiration_time")
            if expiration_time:
                try:
                    if float(expiration_time) < current_time:
                        self.logger.warning(
                            "License expiration_time is in the past for %s: %s",
                            license_path,
                            expiration_time,
                        )
                except ValueError:
                    self.logger.warning(
                        "License has invalid expiration_time in %s: %s",
                        license_path,
                        expiration_time,
                    )
            add_on = self._find_cloud_connected_add_on(payload_root)
            if add_on is None:
                continue

            cloud_product_name = add_on.get("name")
            if not cloud_product_name:
                self.logger.warning("Skipping license without add_on name: %s", license_path)
                continue
            if cloud_product_name not in CLOUD_PRODUCT_METADATA:
                self.logger.warning(
                    "Skipping unsupported cloud product license: product=%s path=%s",
                    cloud_product_name,
                    license_path,
                )
                continue

            cloud_product_label = payload_root.findtext("label")
            if not cloud_product_label:
                self.logger.warning("Skipping license without payload label: %s", license_path)
                continue

            metadata = CLOUD_PRODUCT_METADATA.get(cloud_product_name, {})
            discovered.append(
                {
                    "license_xml": license_xml,
                    # add_ons section is required only as hints for activations that come from licenses on LM
                    # for licenses embedded in the Splunk Apps this can be empty.
                    "add_ons": {},
                    "cloud_product_name": cloud_product_name,
                    "status": statuses.get(cloud_product_name, CLOUD_PRODUCT_STATUS_DEACTIVATED),
                    "full_name": metadata.get("full_name"),
                    "description": metadata.get("description"),
                    "href": metadata.get("href"),
                }
            )

        return discovered

    def _get_server_info_add_ons(self, session_key: str) -> Dict[str, Any]:
        resp, content = SCSUtils.simple_request_with_retry(
            logger=self.logger,
            method="GET",
            path=SPLUNK_SERVER_INFO_URI,
            session_key=session_key,
            getargs={"output_mode": "json"},
        )
        status_code = getattr(resp, "status", None) if resp else None
        if status_code != http.client.OK or not content:
            raise RuntimeError(f"Failed to fetch server info: status={status_code}")

        data = json.loads(content)
        entries = data.get("entry") or []
        if not isinstance(entries, list):
            raise ValueError("server/info response entry is not a list")
        if not entries:
            return {}

        first_entry = entries[0] if isinstance(entries[0], dict) else {}
        content_dict = first_entry.get("content") or {}
        if not isinstance(content_dict, dict):
            raise ValueError("server/info entry.content is not an object")

        add_ons = content_dict.get("addOns") or {}
        if not isinstance(add_ons, dict):
            raise ValueError("server/info addOns is not an object")
        return add_ons

    def _add_special_server_info_product(
        self,
        discovered: List[Dict[str, Any]],
        session_key: str,
        statuses: Dict[str, str],
    ) -> None:
        SPECIAL_SERVER_INFO_PRODUCT_LABEL = "Enterprise Security Premier"
        SPECIAL_SERVER_INFO_LICENSE_SOURCE_NAMES = (
            "es_editions_essentials",
        )
        SPECIAL_SERVER_INFO_PRODUCT_NAMES = (
            "es_editions_premier",
            "es_editions",
        )

        add_ons = self._get_server_info_add_ons(session_key)

        source_entry = next(
            (
                item for item in discovered
                if item.get("cloud_product_name") in SPECIAL_SERVER_INFO_LICENSE_SOURCE_NAMES
            ),
            None,
        )
        if source_entry is None:
            self.logger.warning(
                "Skipping %s discovery because no source license was found in scanned license files",
                SPECIAL_SERVER_INFO_PRODUCT_NAMES[0],
            )
            return

        for special_product_name in SPECIAL_SERVER_INFO_PRODUCT_NAMES:
            special_add_on = add_ons.get(special_product_name)
            if not isinstance(special_add_on, dict):
                continue

            parameters = special_add_on.get("parameters") or {}
            if not isinstance(parameters, dict):
                continue

            if (
                special_product_name == "es_editions_premier"
                and parameters.get("cloud_connected") != "1"
            ):
                continue

            if any(
                item.get("cloud_product_name") == special_product_name
                for item in discovered
            ):
                continue

            metadata = CLOUD_PRODUCT_METADATA.get(special_product_name, {})
            discovered.append(
                {
                    "license_xml": source_entry["license_xml"],
                    "add_ons": {
                        special_product_name: special_add_on
                    },
                    "cloud_product_name": special_product_name,
                    "status": statuses.get(
                        special_product_name,
                        CLOUD_PRODUCT_STATUS_DEACTIVATED,
                    ),
                    "full_name": metadata.get("full_name"),
                    "description": metadata.get("description"),
                    "href": metadata.get("href"),
                }
            )

    @_require_capability(CAPABILITY_GET_CLOUD_CONNECTION_PRODUCT)
    def list_cloud_product_activations(
        self,
        splunk_ctx: SplunkContext,
    ) -> ListCloudProductActivationsResponseBuilder:
        """GET /v1alpha1/cloud-product-connection - list discoverable cloud products."""
        try:
            session_key = splunk_ctx.authtoken
            system_key = splunk_ctx.system_authtoken
            statuses = self._get_discovery_statuses(system_key)
            discovered = self._scan_discoverable_licenses(statuses)
            self._add_special_server_info_product(discovered, system_key, statuses)
            # Convert dictionaries to CloudProductActivationDiscovery instances
            discovered_models = [
                CloudProductActivationDiscovery.from_dict(item) for item in discovered
            ]
            return ListCloudProductActivationsResponseBuilder.ok(discovered_models)
        except Exception as e:
            self.logger.error("Failed to list cloud product activations: %s", e, exc_info=True)
            return ListCloudProductActivationsResponseBuilder.internal_server_error()

    # ========== Activation Helper Methods ==========

    def _get_activation_config(
        self,
        session_key: str
    ) -> tuple:
        """
        Get and validate cloud connection configuration for activation.

        Returns:
            Tuple of (config_dict, error_response)
        """
        try:
            connection_config = get_cloud_connection_config(session_key, self.logger)
        except CloudConnectionConfigNotFoundError:
            self.logger.error("Cloud connection config not found")
            return None, ActivateCloudProductResponseBuilder.forbidden()
        except Exception as e:
            self.logger.error("Failed to read cloud connection config: %s", e)
            return None, ActivateCloudProductResponseBuilder.internal_server_error()

        # Verify cloud connection is enabled
        connection_state = connection_config.get(GENERAL_CONNECTION_STATE_KEY)
        if connection_state != CONNECTION_STATE_ENABLED:
            self.logger.error("Cloud connection is not enabled. connection_state=%s", connection_state)
            return None, ActivateCloudProductResponseBuilder.forbidden()

        # Validate required fields
        tenant_name = connection_config.get(GENERAL_TENANT_NAME_KEY)
        region = connection_config.get('region')
        sp_id = connection_config.get('spID')

        if not tenant_name:
            self.logger.error("Tenant name not found in configuration")
            return None, ActivateCloudProductResponseBuilder.internal_server_error()

        if not region:
            self.logger.error("Region not found in configuration")
            return None, ActivateCloudProductResponseBuilder.internal_server_error()

        if not sp_id:
            self.logger.error("Service Principal ID not found in configuration")
            return None, ActivateCloudProductResponseBuilder.internal_server_error()

        return connection_config, None

    def _extract_license_guid(
        self,
        license_xml: str,
    ) -> tuple:
        """Extract and validate the license GUID from an activation license XML."""
        try:
            license_root = ET.fromstring(license_xml)
            guid_element = license_root.find('.//payload/guid')

            if guid_element is None or not guid_element.text:
                self.logger.error("GUID not found in license XML")
                return None, ActivateCloudProductResponseBuilder.bad_request()

            license_guid = guid_element.text.strip()
            try:
                UUID(license_guid)
            except (ValueError, AttributeError):
                self.logger.error("Invalid GUID format in license XML: %s", license_guid)
                return None, ActivateCloudProductResponseBuilder.bad_request()

            return license_guid, None
        except (ET.ParseError, DefusedXmlException) as e:
            self.logger.error("Failed to parse license XML: %s", e, exc_info=True)
            return None, ActivateCloudProductResponseBuilder.bad_request()
        except Exception as e:
            self.logger.error("Failed to parse license data: %s", e, exc_info=True)
            return None, ActivateCloudProductResponseBuilder.internal_server_error()

    def _extract_add_on_license_guid(
        self,
        add_ons: Any,
        cloud_product_name: str,
    ) -> tuple:
        """Extract the product-specific license GUID from add_ons when present."""
        if not isinstance(add_ons, dict):
            return None, None

        add_on = add_ons.get(cloud_product_name)
        if not isinstance(add_on, dict):
            return None, None

        parameters = add_on.get("parameters") or {}
        if not isinstance(parameters, dict):
            self.logger.error(
                "Invalid add_on parameters for cloud product: %s",
                cloud_product_name,
            )
            return None, None

        license_guid = parameters.get("guid")
        if not license_guid:
            return None, None

        license_guid = str(license_guid).strip()
        try:
            UUID(license_guid)
        except (ValueError, AttributeError):
            self.logger.error(
                "Invalid GUID format in add_on parameters for cloud product %s: %s",
                cloud_product_name,
                license_guid,
            )
            return None, ActivateCloudProductResponseBuilder.bad_request()

        return license_guid, None

    def _extract_product_license_guid(
        self,
        license_xml: str,
        add_ons: Any,
        cloud_product_name: str,
    ) -> tuple:
        """Extract the GUID that belongs to the activated product.

        Some products, notably es_editions_premier, reuse the Essentials embedded
        license XML but identify the actual product license in server/info addOns.
        Prefer that product-specific add_on GUID when present, and otherwise fall
        back to the embedded license XML GUID.
        """
        add_on_guid, error = self._extract_add_on_license_guid(
            add_ons,
            cloud_product_name,
        )
        if error:
            return None, error
        if add_on_guid:
            return add_on_guid, None

        return self._extract_license_guid(license_xml)

    def _check_product_already_activated(
        self,
        session_key: str,
        cloud_product_name: str
    ) -> bool:
        """
        Check if a product is already activated in the configuration.

        Args:
            session_key: The Splunk session key
            cloud_product_name: The name of the cloud product to check

        Returns:
            True if product is already activated, False otherwise
        """
        try:
            conf_entries = get_cloud_connection_conf_entries(
                logger=self.logger,
                session_key=session_key,
            )
            stanzas = self._find_general_and_product_stanzas(conf_entries)

            product_stanza_name = f"{PRODUCT_STANZA_PREFIX}{cloud_product_name}"
            product_content = stanzas.get(product_stanza_name)

            if product_content:
                product_status = product_content.get(PRODUCT_STATUS_KEY, '').strip().lower()
                if product_status == CLOUD_PRODUCT_STATUS_ACTIVATED.lower():
                    self.logger.info(
                        "Product already activated: cloud_product_name=%s",
                        cloud_product_name
                    )
                    return True

            return False
        except Exception as e:
            self.logger.error(
                "Failed to check if product is already activated: %s",
                e,
                exc_info=True
            )
            # Return False to allow activation attempt (fail-open)
            return False

    def _get_activation_keys(
        self,
        session_key: str,
        cloud_product_name: str,
        issuer_id: str,
    ) -> tuple:
        """
        Generate or retrieve cryptographic keys for product SP activation.

        The keypair is stored under the canonical keypair realm, which groups
        products in the same identity family (e.g. es_editions_essentials and
        es_editions_premier) so they share a single registered public key with
        SCS. If a keypair already exists (re-activation or edition sibling), it
        is reused.

        Returns:
            Tuple of (jwk, error_response) where jwk is the product SP's public
            JWK to send as the publicKey payload in the Commerce activation request.
        """
        try:
            sm = SecretManager(logger=self.logger)
            keypair_realm = get_product_family(cloud_product_name)
            if keypair_realm is None:
                self.logger.error(
                    "Unknown cloud product name: %s", cloud_product_name
                )
                return None, ActivateCloudProductResponseBuilder.bad_request()

            # Reuse existing keypair on re-activation or when a sibling edition was previously activated
            existing = sm.get_private_key_and_kid(
                session_key=session_key,
                realm=keypair_realm,
            )
            if existing:
                private_key, kid = existing
                self.logger.info(
                    "Reusing existing keypair for product SP: product=%s keypair_realm=%s kid=%s",
                    cloud_product_name, keypair_realm, kid,
                )
            else:
                private_key = SCSUtils.generate_ecdsa_private_key(self.logger)
                kid = SCSUtils.build_kid_from_issuer_id(issuer_id)
                sm.upsert_private_key_and_kid(
                    session_key=session_key,
                    realm=keypair_realm,
                    private_key_pem=private_key,
                    kid=kid,
                )
                self.logger.info(
                    "Generated new keypair for product SP: product=%s keypair_realm=%s kid=%s",
                    cloud_product_name, keypair_realm, kid,
                )

            public_key = SCSUtils.derive_ecdsa_public_key(self.logger, private_key)
            jwk = SCSUtils.create_ecdsa_jwk(public_key=public_key, kid=kid)

            return jwk, None

        except Exception as e:
            self.logger.error("Failed to prepare product SP keys: %s", e, exc_info=True)
            return None, ActivateCloudProductResponseBuilder.internal_server_error()

    def _get_activation_access_token(
        self,
        session_key: str,
        user: str,
        sp_id: str,
        tenant_name: str,
    ) -> tuple:
        """
        Generate access token for product activation.

        The activation request is signed with the bootstrap SP keypair — the
        bootstrap SP is the caller identity that Commerce authenticates. The
        product keypair is only used as the publicKey payload in the Commerce
        request body, not for signing this request.

        Returns:
            Tuple of (access_token, error_response)
        """
        try:
            # The bootstrap SP is the caller identity for all cloud product activation
            # requests — it is the only principal with the authority to call Commerce
            # before a product SP exists. The product keypair is only used as the
            # publicKey payload in the request body, not for signing this JWT.
            sm = SecretManager(logger=self.logger)
            bootstrap_key_data = sm.get_private_key_and_kid(session_key=session_key, realm=APP_NAME)
            if not bootstrap_key_data:
                self.logger.error("Bootstrap key data not found in secret storage")
                return None, ActivateCloudProductResponseBuilder.internal_server_error()
            bootstrap_private_key, bootstrap_kid = bootstrap_key_data

            access_token = SCSUtils.create_principal_access_token(
                logger=self.logger,
                session_key=session_key,
                splunk_user=user,
                principal_id=sp_id,
                kid=bootstrap_kid,
                private_key=bootstrap_private_key,
                tenant_name=tenant_name,
            )
            return access_token, None
        except Exception as e:
            self.logger.error("Failed to generate access token: %s", e)
            return None, ActivateCloudProductResponseBuilder.internal_server_error()

    def _handle_scs_activation_response(
        self,
        response
    ) -> tuple:
        """
        Handle SCS activation API response and return full response data or error.

        Returns:
            Tuple of (response_data, error_response)
            response_data is the full JSON response dict from SCS, or None on error
        """
        status_code = response.status_code

        if status_code == http.client.ACCEPTED:
            try:
                response_data = response.json()
                self.logger.info("Successfully received SCS activation response")
                # Return full response data for validation at caller level
                return response_data, None

            except (json.JSONDecodeError, ValueError) as e:
                self.logger.error("Failed to parse SCS response: %s", e)
                return None, ActivateCloudProductResponseBuilder.internal_server_error()

        # Handle error status codes
        if status_code == http.client.NOT_FOUND:
            self.logger.error("Tenant not found or operation not authorized: 404")
            return None, ActivateCloudProductResponseBuilder.forbidden()
        elif status_code == http.client.UNPROCESSABLE_ENTITY:
            self.logger.error("Invalid license: SCS rejected activation with 422")
            return None, ActivateCloudProductResponseBuilder(Response(400, json.dumps({'message': 'Invalid license'}), {'Content-Type': 'application/json'}))
        elif status_code == http.client.BAD_REQUEST:
            self.logger.error("Bad request: 400")
            return None, ActivateCloudProductResponseBuilder.bad_request()
        elif status_code == http.client.UNAUTHORIZED:
            self.logger.error("Unauthorized: 401")
            return None, ActivateCloudProductResponseBuilder.unauthorized()
        elif status_code == http.client.FORBIDDEN:
            self.logger.error("Forbidden: 403")
            return None, ActivateCloudProductResponseBuilder.forbidden()
        elif status_code == http.client.TOO_MANY_REQUESTS:
            self.logger.error("Rate limited: 429")
            return None, ActivateCloudProductResponseBuilder.too_many_requests()

        self.logger.error("SCS product activation failed: status=%s, body=%s", status_code, response.content)
        return None, ActivateCloudProductResponseBuilder.internal_server_error()

    def _call_scs_activation_api(
        self,
        session_key: str,
        user: str,
        tenant_name: str,
        issuer_id: str,
        license_xml: str,
        addons,
        jwk: dict,
        access_token: str
    ) -> tuple:
        """
        Call SCS Commerce API to activate product.

        Args:
            addons: Dictionary of add-ons

        Returns:
            Tuple of (response_data, error_response)
            response_data is the full JSON response dict from SCS, or None on error
        """
        try:
            activation_url = get_commerce_api_uri_cloud_product(session_key, tenant_name, issuer_id)
            self.logger.info("Calling SCS product activation API at: %s", activation_url)
        except Exception as e:
            self.logger.error("Failed to construct activation URL: %s", e)
            return None, ActivateCloudProductResponseBuilder.internal_server_error()

        license_xml_b64 = base64.b64encode(license_xml.encode('utf-8')).decode('utf-8')
        payload = {
            "licenseFileXml": license_xml_b64,
            "publicKey": jwk,
            "addOns": addons,
        }

        try:
            # this call isn't idempotent; we cannot retry activating
            # the same product under high latency because commerce
            # may have already started activation and will return a 409
            response = tracked_request_with_splunkd_proxy(
                session_key=session_key,
                logger=self.logger,
                operation=OPERATION_ACTIVATE_CLOUD_PRODUCT,
                method='POST',
                url=activation_url,
                splunk_user=user,
                access_token=access_token,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=SCSUtils._get_connection_config(self.logger, session_key)['long_timeout'],
                retry_read=0,
            )

            self.logger.info("SCS activation response: %s", response.content)
            return self._handle_scs_activation_response(response)

        except Exception as e:
            self.logger.error("Failed to call SCS product activation API: %s", e, exc_info=True)
            return None, ActivateCloudProductResponseBuilder.internal_server_error()

    def _store_product_activation(
        self,
        session_key: str,
        cloud_product_name: str,
        status: str,
        sp_id: str = None,
        license_guid: str = None,
        product_code: str = None,
        app_conf_hash: str = None,
    ) -> None:
        """
        Store product activation details in cloud-connection.conf.

        Can be used to store either complete activation details or minimal failure state.
        When sp_id, license_guid, and product_code are provided, stores full activation.
        When only status is provided, stores minimal state (e.g., for failures).

        Args:
            session_key: Splunk session key
            cloud_product_name: Name of the cloud product
            status: Product status (e.g., activated, activation-failed, etc.)
            sp_id: Service principal ID (optional)
            license_guid: License GUID (optional)
            product_code: Product code (optional)
            app_conf_hash: SHA-256 hash of the ES default/app.conf file (optional)

        Non-fatal if it fails - product state may already be persisted.
        """
        try:
            product_stanza_name = f"{PRODUCT_STANZA_PREFIX}{cloud_product_name}"
            # POST to the stanza URL so create/update targets one stanza (upsert),
            # instead of POSTing to the collection endpoint with a `name` field.
            conf_path = f'/servicesNS/nobody/{APP_NAME}/configs/conf-cloud-connection'
            product_stanza_conf_path = f'/servicesNS/nobody/{APP_NAME}/configs/conf-cloud-connection/{product_stanza_name}'
            # Build postargs with required fields (stanza name is in the path only)
            product_data = {
                PRODUCT_STATUS_KEY: status,
                PRODUCT_NAME_KEY: cloud_product_name,
            }

            # Add optional fields if provided
            if sp_id is not None:
                product_data[PRODUCT_SP_ID_KEY] = sp_id
            if license_guid is not None:
                product_data[PRODUCT_LICENSE_GUID_KEY] = license_guid
            if product_code is not None:
                product_data[PRODUCT_PRODUCT_CODE_KEY] = product_code
            if app_conf_hash is not None:
                product_data[PRODUCT_APP_CONF_HASH_KEY] = app_conf_hash

            # perform a fetch on the stanza to check if it exists
            get_resp, _get_content = SCSUtils.simple_request_with_retry(
                logger=self.logger,
                method='GET',
                path=product_stanza_conf_path,
                session_key=session_key,
                getargs={'output_mode': 'json'},
            )
            if get_resp and getattr(get_resp, 'status', None) == http.client.OK:
                # if stanza exists use product stanza specific path to update
                conf_path = product_stanza_conf_path
            else:
                # if stanza does not exist, add stanza name to payload
                product_data['name'] = product_stanza_name

            resp, content = SCSUtils.simple_request_with_retry(
                logger=self.logger,
                method='POST',
                path=conf_path,
                session_key=session_key,
                postargs=product_data
            )

            status_code = getattr(resp, 'status', None) if resp else None
            if status_code not in (http.client.OK, http.client.CREATED):
                self.logger.error("Failed to store product activation in config: status=%s", status_code)
            else:
                self.logger.info("Stored product activation state: %s (status=%s)", cloud_product_name, status)
        except Exception as e:
            self.logger.error("Failed to store product activation details: %s", e)

    # ========== Deactivation Helper Methods ==========

    def _update_product_status(
        self,
        session_key: str,
        cloud_product_name: str,
        status: str
    ) -> None:
        """
        Update product status in cloud-connection.conf.

        Args:
            session_key: Splunk session key for authentication
            cloud_product_name: The cloud product name
            status: New status value (e.g., 'deactivated')

        Raises:
            Exception: If the update fails
        """
        try:
            product_stanza_name = f"{PRODUCT_STANZA_PREFIX}{cloud_product_name}"
            conf_path = f'/servicesNS/nobody/{APP_NAME}/configs/conf-cloud-connection/{product_stanza_name}'

            product_data = {
                PRODUCT_STATUS_KEY: status,
            }

            resp, content = SCSUtils.simple_request_with_retry(
                logger=self.logger,
                method='POST',
                path=conf_path,
                session_key=session_key,
                postargs=product_data
            )

            status_code = getattr(resp, 'status', None) if resp else None
            if status_code not in (http.client.OK, http.client.CREATED):
                self.logger.error(
                    "Failed to update product status in config: status=%s cloud_product_name=%s",
                    status_code,
                    cloud_product_name
                )
                raise Exception(f"Failed to update product status: HTTP {status_code}")

            self.logger.info(
                "Successfully updated product status: cloud_product_name=%s status=%s",
                cloud_product_name,
                status
            )
        except Exception as e:
            self.logger.error(
                "Failed to update product status: cloud_product_name=%s error=%s",
                cloud_product_name,
                e
            )
            raise

    def _remove_product_from_config(
        self,
        session_key: str,
        cloud_product_name: str
    ) -> None:
        """
        Remove product configuration from cloud-connection.conf.

        This method deletes the entire product stanza from the configuration file.

        Args:
            session_key: Splunk session key for authentication
            cloud_product_name: The cloud product name

        Raises:
            Exception: If the deletion fails
        """
        try:
            product_stanza_name = f"{PRODUCT_STANZA_PREFIX}{cloud_product_name}"
            conf_path = f'/servicesNS/nobody/{APP_NAME}/configs/conf-cloud-connection/{product_stanza_name}'

            resp, content = SCSUtils.simple_request_with_retry(
                logger=self.logger,
                method='DELETE',
                path=conf_path,
                session_key=session_key
            )

            status_code = getattr(resp, 'status', None) if resp else None
            if status_code not in (http.client.OK, http.client.NO_CONTENT):
                self.logger.error(
                    "Failed to remove product from config: status=%s cloud_product_name=%s",
                    status_code,
                    cloud_product_name
                )
                raise Exception(f"Failed to remove product from config: HTTP {status_code}")

            self.logger.info(
                "Successfully removed product from config: cloud_product_name=%s",
                cloud_product_name
            )
        except Exception as e:
            self.logger.error(
                "Failed to remove product from config: cloud_product_name=%s error=%s",
                cloud_product_name,
                e
            )
            raise

    def _remove_product_token(
        self,
        session_key: str,
        cloud_product_name: str
    ) -> None:
        """
        Remove the stored access token for a cloud product.

        The private key and kid are retained so the keypair can be reused on
        re-activation without needing to re-register a new public key with SCS.

        This is a non-fatal operation - if removal fails, it will be logged
        but will not prevent the deactivation from succeeding.

        Args:
            session_key: Splunk session key for authentication
            cloud_product_name: The cloud product name (used as realm)
        """
        sm = SecretManager(logger=self.logger)
        product_family = get_product_family(cloud_product_name)
        if product_family is None:
            self.logger.warning(
                "Skipping access token removal for unknown cloud product: %s",
                cloud_product_name,
            )
            return

        try:
            sm.delete_secret(
                session_key=session_key,
                realm=product_family,
                key_name=SP_ACCESS_TOKEN_SECRET_NAME,
            )
            self.logger.info(
                "Successfully removed %s: cloud_product_name=%s",
                SP_ACCESS_TOKEN_SECRET_NAME, cloud_product_name,
            )
        except Exception as e:
            self.logger.warning(
                "Failed to remove %s (non-fatal): cloud_product_name=%s error=%s",
                SP_ACCESS_TOKEN_SECRET_NAME, cloud_product_name, e,
            )

    def refresh_cloud_product_activation(
        self,
        session_key: str,
        user: str,
        cloud_product_name: str,
        license_xml: str,
        add_ons: Dict[str, Any],
    ) -> bool:
        """
        Re-send an already activated product to Commerce.

        This is used by periodic Extension App upgrade detection. It intentionally
        preserves the existing local product status on failure so the next
        modular input run can retry the refresh.
        """
        try:
            connection_config, error = self._get_activation_config(session_key)
            if error:
                self.logger.error(
                    "Cannot refresh product activation without enabled cloud connection: %s",
                    cloud_product_name,
                )
                return False

            tenant_name = connection_config[GENERAL_TENANT_NAME_KEY]
            sp_id = connection_config['spID']

            deployment_id = SearchHeadUnit.get_deployment_id(self.logger, session_key)
            if deployment_id is None:
                self.logger.error("Failed to get deployment ID for product refresh")
                return False
            issuer_id = str(deployment_id)

            license_guid, error = self._extract_product_license_guid(
                license_xml,
                add_ons,
                cloud_product_name,
            )
            if error:
                self.logger.error(
                    "Cannot refresh product activation with invalid license data: %s",
                    cloud_product_name,
                )
                return False

            jwk, error = self._get_activation_keys(
                session_key, cloud_product_name, issuer_id
            )
            if error:
                return False

            access_token, error = self._get_activation_access_token(
                session_key, user, sp_id, tenant_name
            )
            if error:
                return False

            scs_response, error = self._call_scs_activation_api(
                session_key,
                user,
                tenant_name,
                issuer_id,
                license_xml,
                add_ons,
                jwk,
                access_token,
            )
            if error:
                return False

            required_fields = ['spID', 'productCode', 'status']
            for field in required_fields:
                if not scs_response.get(field):
                    self.logger.error(
                        "%s not found in SCS refresh response for %s",
                        field,
                        cloud_product_name,
                    )
                    return False

            internal_status = CLOUD_PRODUCT_STATUS_REVERSE_MAPPING.get(
                scs_response['status']
            )
            if internal_status != CLOUD_PRODUCT_STATUS_ACTIVATED:
                self.logger.error(
                    "Commerce refresh did not return active status: product=%s api_status=%s internal_status=%s",
                    cloud_product_name,
                    scs_response.get('status'),
                    internal_status,
                )
                return False

            sp_id_from_response = scs_response['spID']
            product_code_from_response = scs_response['productCode']
            self._store_product_activation(
                session_key=session_key,
                cloud_product_name=cloud_product_name,
                status=internal_status,
                sp_id=sp_id_from_response,
                license_guid=license_guid,
                product_code=product_code_from_response,
            )

            try:
                sm = SecretManager(logger=self.logger)
                sm.upsert_secret(
                    session_key=session_key,
                    realm=APP_NAME,
                    key_name=SP_ACCESS_TOKEN_SECRET_NAME,
                    value=access_token,
                )
            except Exception as e:
                self.logger.error(
                    "Failed to store bootstrap access token after product refresh (non-fatal): "
                    "cloud_product_name=%s error=%s",
                    cloud_product_name,
                    e,
                )

            try:
                sm = SecretManager(logger=self.logger)
                keypair_realm = get_product_family(cloud_product_name)
                if keypair_realm is None:
                    self.logger.error(
                        "Cannot store product SP access token for unknown cloud product: %s",
                        cloud_product_name,
                    )
                    return False
                key_data = sm.get_private_key_and_kid(
                    session_key=session_key,
                    realm=keypair_realm,
                )
                if not key_data:
                    self.logger.error(
                        "Product keypair not found after refresh: cloud_product_name=%s",
                        cloud_product_name,
                    )
                    return False

                product_private_key, product_kid = key_data
                generate_and_store_access_token(
                    session_key=session_key,
                    secret_manager=sm,
                    realm=keypair_realm,
                    kid=product_kid,
                    private_key=product_private_key,
                    principal_id=sp_id_from_response,
                    tenant_name=tenant_name,
                    splunk_user=user,
                    logger=self.logger,
                )
            except Exception as e:
                self.logger.error(
                    "Failed to store product SP access token after refresh: "
                    "cloud_product_name=%s error=%s",
                    cloud_product_name,
                    e,
                )
                return False

            self.logger.info(
                "Refreshed product activation: cloud_product_name=%s",
                cloud_product_name,
            )
            return True

        except Exception as e:
            self.logger.error(
                "Unexpected error during product activation refresh: %s",
                e,
                exc_info=True,
            )
            return False

    # ========== Main Product Methods ==========

    @_require_capability(CAPABILITY_EDIT_CLOUD_CONNECTION)
    def activate_cloud_product(
        self,
        splunk_ctx: SplunkContext,
        request: 'CloudProductActivation',
    ) -> ActivateCloudProductResponseBuilder:
        """
        POST /v1alpha1/cloud-product-connection - Activate a cloud product connection

        This endpoint activates a cloud product by sending license information to SCS.

        Args:
            splunk_ctx: Splunk context with session key and user
            request: CloudProductActivation request with license_xml and optional hint

        Returns:
            ActivateCloudProductResponseBuilder with the cloud product name on success
        """
        try:
            session_key = splunk_ctx.authtoken
            system_key = splunk_ctx.system_authtoken
            user = splunk_ctx.user

            self.logger.info("Starting cloud product activation")

            # Step 1: Get and validate configuration
            connection_config, error = self._get_activation_config(system_key)
            if error:
                return error

            tenant_name = connection_config[GENERAL_TENANT_NAME_KEY]
            sp_id = connection_config['spID']

            # Step 2: Get issuer ID
            deployment_id = SearchHeadUnit.get_deployment_id(self.logger, system_key)
            if deployment_id is None:
                self.logger.error("Failed to get deployment ID")
                return ActivateCloudProductResponseBuilder.internal_server_error()
            issuer_id = str(deployment_id)

            # Step 3: Get license information from request
            license_xml = request.license_xml
            cloud_product_name = request.cloud_product_name
            add_ons = request.add_ons
            self.logger.info("Received add-on info: %s", add_ons)

            license_guid, error = self._extract_product_license_guid(
                license_xml,
                add_ons,
                cloud_product_name,
            )
            if error:
                return error

            self.logger.info(
                "Parsed license data: license_guid=%s, cloud_product_name=%s",
                license_guid,
                cloud_product_name
            )

            if get_product_family(cloud_product_name) is None:
                self.logger.error("Unknown cloud product name: %s", cloud_product_name)
                return ActivateCloudProductResponseBuilder.bad_request()

            # Step 3a: Check if product is already activated
            if self._check_product_already_activated(system_key, cloud_product_name):
                self.logger.warning(
                    "Attempted to activate already activated product: %s",
                    cloud_product_name
                )
                return ActivateCloudProductResponseBuilder.conflict()

            # Step 4: Get cryptographic keys for the product SP
            jwk, error = self._get_activation_keys(system_key, cloud_product_name, issuer_id)
            if error:
                return error

            # Step 5: Get access token signed by the bootstrap SP
            access_token, error = self._get_activation_access_token(
                system_key, user, sp_id, tenant_name
            )
            if error:
                return error

            # Step 6: Call SCS activation API
            scs_response, error = self._call_scs_activation_api(
                system_key, user, tenant_name, issuer_id,
                license_xml, add_ons, jwk, access_token
            )
            if error:
                # Persist activation failure state
                self._store_product_activation(
                    system_key,
                    cloud_product_name,
                    CLOUD_PRODUCT_STATUS_ACTIVATION_FAILED
                )
                CloudConnectionEventLog(session_key, self.logger).log(
                    operation=OPERATION_ACTIVATE_CLOUD_PRODUCT,
                    event_type=AUDIT_EVENT_PRODUCT_ACTIVATION_FAILURE,
                    severity=AUDIT_SEVERITY_ERROR,
                )
                return error

            # Validate required fields in SCS response
            required_fields = ['spID', 'productCode', 'status']
            for field in required_fields:
                if not scs_response.get(field):
                    self.logger.error("%s not found in SCS response", field)
                    # Persist activation failure state
                    self._store_product_activation(
                        system_key,
                        cloud_product_name,
                        CLOUD_PRODUCT_STATUS_ACTIVATION_FAILED
                    )
                    CloudConnectionEventLog(session_key, self.logger).log(
                        operation=OPERATION_ACTIVATE_CLOUD_PRODUCT,
                        event_type=AUDIT_EVENT_PRODUCT_ACTIVATION_FAILURE,
                        severity=AUDIT_SEVERITY_ERROR,
                    )
                    return ActivateCloudProductResponseBuilder.internal_server_error()

            sp_id_from_response = scs_response['spID']
            product_code_from_response = scs_response['productCode']
            status_from_response = scs_response['status']

            # Map API status to internal status for storage
            # SCS returns API status values (active, inactive, fulfilling, failed)
            # We store internal status values (activated, deactivated, in-progress, activation-failed)
            # If status is not recognized, default to activation-failed for safety
            internal_status = CLOUD_PRODUCT_STATUS_REVERSE_MAPPING.get(
                status_from_response
            )

            if internal_status is None:
                # Unknown status from SCS - set to activation-failed for safety
                self.logger.warning(
                    "Unknown status from SCS during activation: api_status=%s, defaulting to activation-failed",
                    status_from_response
                )
                internal_status = CLOUD_PRODUCT_STATUS_ACTIVATION_FAILED

            self.logger.info(
                "Product activation response processed: spId=%s, productCode=%s, api_status=%s, internal_status=%s",
                sp_id_from_response,
                product_code_from_response,
                status_from_response,
                internal_status
            )

            app_conf_hash = None
            if is_es_edition_product(cloud_product_name):
                app_conf_hash = compute_es_app_conf_hash(self.logger)

            # Step 7: Store activation details with internal status (non-fatal)
            self._store_product_activation(
                session_key=system_key,
                cloud_product_name=cloud_product_name,
                status=internal_status,
                sp_id=sp_id_from_response,
                license_guid=license_guid,
                product_code=product_code_from_response,
                app_conf_hash=app_conf_hash,
            )

            # Step 8: Store access token in secrets (non-fatal)
            # This access token is from bootstrap SP
            try:
                sm = SecretManager(logger=self.logger)
                sm.upsert_secret(
                    session_key=system_key,
                    realm=APP_NAME,
                    key_name=SP_ACCESS_TOKEN_SECRET_NAME,
                    value=access_token
                )
                self.logger.info("Successfully stored access token for bootstrap")
            except Exception as e:
                self.logger.error(
                    "Failed to store access token (non-fatal): cloud_product_name=%s error=%s",
                    cloud_product_name,
                    e
                )

            # Step 9: Generate and store product SP access token immediately (non-fatal).
            # The GET /cloud-connection/{product} handler calls _refresh_access_token which
            # requires sp_access_token to already exist for the product realm. Without this,
            # the token is only written by the daily key rotation cycle, leaving the UI broken
            # for up to 24 hours after every activation or edition upgrade.
            if internal_status == CLOUD_PRODUCT_STATUS_ACTIVATED:
                try:
                    sm = SecretManager(logger=self.logger)
                    keypair_realm = get_product_family(cloud_product_name)
                    if keypair_realm is None:
                        self.logger.error(
                            "Cannot store initial product SP access token for unknown cloud product: %s",
                            cloud_product_name,
                        )
                        key_data = None
                    else:
                        key_data = sm.get_private_key_and_kid(
                            session_key=system_key,
                            realm=keypair_realm,
                        )
                    if key_data:
                        product_private_key, product_kid = key_data
                        generate_and_store_access_token(
                            session_key=system_key,
                            secret_manager=sm,
                            realm=keypair_realm,
                            kid=product_kid,
                            private_key=product_private_key,
                            principal_id=sp_id_from_response,
                            tenant_name=tenant_name,
                            splunk_user=user,
                            logger=self.logger,
                        )
                        self.logger.info(
                            "Stored initial product SP access token: cloud_product_name=%s",
                            cloud_product_name,
                        )
                    else:
                        self.logger.error(
                            "Product keypair not found after activation (non-fatal): cloud_product_name=%s",
                            cloud_product_name,
                        )
                except Exception as e:
                    self.logger.error(
                        "Failed to store initial product SP access token (non-fatal): "
                        "cloud_product_name=%s error=%s",
                        cloud_product_name,
                        e,
                    )

            if internal_status == CLOUD_PRODUCT_STATUS_ACTIVATED:
                CloudConnectionEventLog(session_key, self.logger).log(
                    operation=OPERATION_ACTIVATE_CLOUD_PRODUCT,
                    event_type=AUDIT_EVENT_PRODUCT_ACTIVATION_SUCCESS,
                    severity=AUDIT_SEVERITY_INFO,
                )
            elif internal_status == CLOUD_PRODUCT_STATUS_ACTIVATION_FAILED:
                CloudConnectionEventLog(session_key, self.logger).log(
                    operation=OPERATION_ACTIVATE_CLOUD_PRODUCT,
                    event_type=AUDIT_EVENT_PRODUCT_ACTIVATION_FAILURE,
                    severity=AUDIT_SEVERITY_ERROR,
                )
                return ActivateCloudProductResponseBuilder.internal_server_error()

            # Return success
            return ActivateCloudProductResponseBuilder.accepted(
                CloudProductActivated(cloud_product_name=cloud_product_name)
            )

        except Exception as e:
            self.logger.error("Unexpected error during cloud product activation: %s", e, exc_info=True)
            CloudConnectionEventLog(session_key, self.logger).log(
                operation=OPERATION_ACTIVATE_CLOUD_PRODUCT,
                event_type=AUDIT_EVENT_PRODUCT_ACTIVATION_FAILURE,
                severity=AUDIT_SEVERITY_ERROR,
            )
            return ActivateCloudProductResponseBuilder.internal_server_error()

    @_require_capability(CAPABILITY_EDIT_CLOUD_CONNECTION)
    def deactivate_cloud_product(
        self,
        splunk_ctx: SplunkContext,
        cloud_product_name: str,
    ) -> DeactivateCloudProductResponseBuilder:
        """
        DELETE /v1alpha1/cloud-product-connection/{cloudProductName} - Deactivate a cloud product

        This endpoint deactivates a cloud product connection by:
        1. Verifying the cloud connection is enabled
        2. Checking that the product exists in configuration
        3. Removing the product configuration from cloud-connection.conf
        4. Removing the stored access token from secrets

        Note: This does NOT call any Commerce API - it only updates local configuration.

        Args:
            splunk_ctx: Splunk context with session key and user
            cloud_product_name: The cloud product name to deactivate

        Returns:
            DeactivateCloudProductResponseBuilder with no_content on success
        """
        try:
            session_key = splunk_ctx.authtoken
            system_key = splunk_ctx.system_authtoken
            self.logger.info("Starting cloud product deactivation: %s", cloud_product_name)

            # Step 1: Get configuration entries and verify cloud connection is enabled
            conf_entries = get_cloud_connection_conf_entries(
                logger=self.logger,
                session_key=system_key,
            )
            stanzas = self._find_general_and_product_stanzas(conf_entries)
            general: Dict[str, Any] = stanzas.get(CONFIG_STANZA)

            connection_state = (general.get(GENERAL_CONNECTION_STATE_KEY) or '').strip().lower()
            if connection_state != CONNECTION_STATE_ENABLED:
                self.logger.warning(
                    'Cloud connection is not enabled. connection_state=%s cloud_product_name=%s',
                    connection_state,
                    cloud_product_name,
                )
                return DeactivateCloudProductResponseBuilder(
                    Response(
                        http.client.NOT_FOUND,
                        json.dumps(
                            {
                                'message': 'Cloud connection is not enabled',
                                'connection_state': connection_state,
                            }
                        ),
                        {'Content-Type': 'application/json'},
                    )
                )

            # Step 2: Verify the product exists in configuration
            product_stanza_name = f"{PRODUCT_STANZA_PREFIX}{cloud_product_name}"
            product_content = stanzas.get(product_stanza_name)
            if not product_content:
                self.logger.warning(
                    'Cloud product not found in config. cloud_product_name=%s',
                    cloud_product_name,
                )
                return DeactivateCloudProductResponseBuilder(
                    Response(
                        http.client.NOT_FOUND,
                        json.dumps(
                            {
                                'message': 'Cloud product not found',
                                'cloud_product_name': cloud_product_name,
                            }
                        ),
                        {'Content-Type': 'application/json'},
                    )
                )

            # Step 3: Update product status to deactivated in cloud-connection.conf
            self._update_product_status(system_key, cloud_product_name, CLOUD_PRODUCT_STATUS_DEACTIVATED)

            # Step 4: Remove access token from secrets
            self._remove_product_token(system_key, cloud_product_name)

            self.logger.info(
                "Successfully deactivated cloud product: %s",
                cloud_product_name
            )
            return DeactivateCloudProductResponseBuilder.no_content()

        except Exception as e:
            self.logger.error("Error deactivating cloud product: %s", e, exc_info=True)
            return DeactivateCloudProductResponseBuilder.internal_server_error()
