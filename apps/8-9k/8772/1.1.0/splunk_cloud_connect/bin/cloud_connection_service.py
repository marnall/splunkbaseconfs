#!/usr/bin/env python3
# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.
"""
Cloud Connection Service Implementation

This module implements the ServiceProtocol interface for handling
cloud connection operations including onboarding, activation, and status retrieval.
"""

import os
import sys

# Add the bin directory to sys.path to ensure correct module imports
# This prevents conflicts with other Splunk apps that may have similarly named modules
bin_dir = os.path.dirname(os.path.abspath(__file__))
if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

import http.client
import json
import logging
import random
import socket
import time
from types import SimpleNamespace
from http import HTTPStatus
from typing import Any, Dict, List, Optional
from uuid import UUID

from constants import (
    APP_NAME,
    AUDIT_EVENT_CONNECTION_STATE_CHANGED,
    AUDIT_EVENT_OTP_REQUESTED,
    AUDIT_EVENT_CLOUD_CONNECTION_CREATED,
    AUDIT_EVENT_CLOUD_CONNECTION_DELETED,
    AUDIT_SEVERITY_INFO,
    CAPABILITY_GET_CLOUD_CONNECTION,
    CAPABILITY_GET_CLOUD_CONNECTION_PRODUCT,
    CAPABILITY_EDIT_CLOUD_CONNECTION,
    CLOUD_PRODUCT_STATUS_ACTIVATED,
    CLOUD_PRODUCT_STATUS_ACTIVATION_FAILED,
    CLOUD_PRODUCT_STATUS_DEACTIVATED,
    CLOUD_PRODUCT_STATUS_REVERSE_MAPPING,
    CONFIG_STANZA,
    CONNECTION_STATE_DISABLED,
    CONNECTION_STATE_ENABLED,
    CONNECTION_STATE_CREATE_FAILED,
    CONNECTION_STATE_IN_PROGRESS,
    CONNECTION_STATE_OTP_REQUESTED,
    CONNECTION_STATE_UNAVAILABLE,
    GENERAL_CONNECTION_STATE_KEY,
    GENERAL_TENANT_NAME_KEY,
    OPERATION_GET_SCS_CONNECTIVITY,
    OPERATION_DELETE_CLOUD_CONNECTION,
    OPERATION_CREATE_CLOUD_CONNECTION_INTAKE,
    OPERATION_CREATE_CLOUD_CONNECTION,
    OPERATION_GET_CLOUD_CONNECTION_PRODUCT,
    PRODUCT_NAME_KEY,
    PRODUCT_PRODUCT_CODE_KEY,
    PRODUCT_SP_ID_KEY,
    PRODUCT_STANZA_PREFIX,
    PRODUCT_LICENSE_GUID_KEY,
    PRODUCT_STATUS_KEY,
    SP_ACCESS_TOKEN_SECRET_NAME,
    SPLUNK_CLOUD_CONNECTION_CONF_URI,
    get_commerce_api_url_base,
    get_commerce_api_uri_cloud_connection,
    get_commerce_api_uri_otp_intake,
    get_uri_cloud_connection_config,
    get_commerce_api_uri_cloud_product,
    get_commerce_api_uri_cloud_product_code,
)
from generated.interface import ServiceProtocol
from generated.models import (
    CloudConnectionDetails,
    CloudConnectionStatus,
    CloudConnectionInfo,
    OnboardingConfig,
    OnboardingInitiated,
    OTPVerification,
    Error,
)
from generated.responses import (
    CreateCloudConnectionIntakeResponseBuilder,
    CreateCloudConnectionResponseBuilder,
    DeleteCloudConnectionResponseBuilder,
    GetCloudConnectionResponseBuilder,
    GetCloudConnectionProductResponseBuilder,
    GetCloudConnectionProductStatusResponseBuilder,
    RequestCloudConnectionOTPResponseBuilder,
    GetSCSConnectivityResponseBuilder,
)
from generated.req_resp import Response, SplunkContext
from utils.access_token_helper import get_valid_access_token
from utils.cloud_connection_event_log import CloudConnectionEventLog
from utils.event_tracker import tracked_request_with_splunkd_proxy
from utils.log import setup_logger
from utils.scs_utils import SCSUtils
from utils.search_head_unit import SearchHeadUnit
from utils.secret_manager import SecretManager
from utils.utils import (
    CloudConnectionConfigNotFoundError,
    get_all_license_guids,
    get_cloud_connection_config,
    get_cloud_connection_conf_entries,
    get_product_family,
    has_capability,
    _require_capability,
    get_product_config,
)

logger = setup_logger("cloud_connection_service", level=logging.INFO)


class CloudConnectionService(ServiceProtocol):
    """
    Service implementation for Cloud Connection API.

    Handles:
    - Retrieving cloud connection status
    - Initiating cloud connection onboarding
    - Verifying OTP and establishing trust
    - Deactivating cloud connections
    """

    def __init__(self):
        """Initialize the cloud connection service."""
        self.logger = logger
        self.logger.info("CloudConnectionService initialized")

    @staticmethod
    def _parse_optional_int(val: Any) -> Optional[int]:
        if val is None:
            return None
        if isinstance(val, bool):
            return None
        if isinstance(val, int):
            return val
        if isinstance(val, str):
            s = val.strip()
            if s == "":
                return None
            try:
                return int(s)
            except ValueError:
                return None
        return None

    @_require_capability(CAPABILITY_GET_CLOUD_CONNECTION_PRODUCT)
    def get_scs_connectivity(
        self, splunk_ctx: SplunkContext
    ) -> GetSCSConnectivityResponseBuilder:
        """
        GET /v1alpha1/cloud-connection/scs - returns response builder object
        """
        try:
            self.logger.info("Checking SCS cloud connectivity.")
            system_key = splunk_ctx.system_authtoken
            # if there's no exception then we are able to connect (need to verify)
            url = get_commerce_api_url_base(system_key)
            response = tracked_request_with_splunkd_proxy(
                session_key=system_key,
                logger=self.logger,
                operation=OPERATION_GET_SCS_CONNECTIVITY,
                method="HEAD",
                url=url,
                splunk_user="system",
                json={},
            )
            self.logger.info(
                "SCS connection to %s was successful with code %s.",
                url,
                response.status_code,
            )
            return GetSCSConnectivityResponseBuilder.ok()

        except Exception as e:
            # a possible case, we are unable to connect to scs
            self.logger.info("Unable to connect to scs: %s", e)
            return GetSCSConnectivityResponseBuilder.service_unavailable()

    @_require_capability(CAPABILITY_GET_CLOUD_CONNECTION)
    def get_cloud_connection(
        self, splunk_ctx: SplunkContext
    ) -> GetCloudConnectionResponseBuilder:
        """
        GET /v1alpha1/cloud-connection - Get cloud connection status

        Returns:
            GetCloudConnectionResponseBuilder with connection information
        """
        try:
            self.logger.info("Getting cloud connection status")

            # Use system_authtoken to read cloud-connection.conf
            system_user_token = splunk_ctx.system_authtoken

            # Read from the general stanza in cloud-connection.conf
            conf_path = "/servicesNS/nobody/splunk_cloud_connect/configs/conf-cloud-connection/general"
            resp, content = SCSUtils.simple_request_with_retry(
                self.logger,
                method="GET",
                path=conf_path,
                session_key=system_user_token,
                getargs={"output_mode": "json"},
            )

            status = getattr(resp, "status", None) if resp else None

            # If the stanza doesn't exist or there's an error, return disabled state
            if status == 404:
                self.logger.info(
                    "No cloud connection configuration found, returning disabled state"
                )
                connection_info = CloudConnectionInfo(
                    connection_state=CONNECTION_STATE_DISABLED
                )
                return GetCloudConnectionResponseBuilder.ok(connection_info)

            if status not in (200, 201):
                self.logger.error(
                    "Failed to read configuration from cloud-connection.conf. "
                    "status=%s",
                    status or "n/a",
                )
                return GetCloudConnectionResponseBuilder.internal_server_error()

            # Parse the configuration from the response
            config_data = json.loads(content)
            entry = config_data.get("entry", [{}])[0]
            content_dict = entry.get("content", {})
            connection_state = content_dict.get(
                "connectionState", CONNECTION_STATE_DISABLED
            )
            self.logger.info("Retrieved connection state: %s", connection_state)

            if connection_state in {CONNECTION_STATE_DISABLED, ""}:
                return GetCloudConnectionResponseBuilder.ok(
                    CloudConnectionInfo(connection_state=CONNECTION_STATE_DISABLED)
                )
            else:
                connection_info = {
                    "connectionState": connection_state,
                }
                for field in [
                    "bootstrapLicenseID",
                    "deploymentId",
                    "otpEmail",
                    "region",
                    "regionAuthHostname",
                    "requestedTenantName",
                    "spID",
                    "tenantApiHostname",
                    "tenantName",
                ]:
                    val = content_dict.get(field, "")
                    if val:
                        connection_info[field] = val
                otp_creation_time = content_dict.get("otpCreationTs", "")
                otp_expiry_seconds = content_dict.get("otpExpirySeconds", "")
                if otp_creation_time:
                    connection_info["otpCreationTs"] = int(otp_creation_time)
                if otp_expiry_seconds:
                    connection_info["otpExpirySeconds"] = int(otp_expiry_seconds)
                return GetCloudConnectionResponseBuilder.ok(
                    CloudConnectionInfo.from_dict(connection_info)
                )

            return GetCloudConnectionResponseBuilder.ok(
                CloudConnectionInfo(connection_state=CONNECTION_STATE_DISABLED)
            )
        except Exception as e:
            self.logger.error("Error getting cloud connection: %s", e)
            return GetCloudConnectionResponseBuilder.internal_server_error()

    @_require_capability(CAPABILITY_EDIT_CLOUD_CONNECTION)
    def delete_cloud_connection(
        self, splunk_ctx: SplunkContext
    ) -> DeleteCloudConnectionResponseBuilder:
        """
        DELETE /v1alpha1/cloud-connection - Deactivate cloud connection

        Resets all fields in the general stanza to their default values.

        Returns:
            DeleteCloudConnectionResponseBuilder with no content on success
        """
        sm = SecretManager(logger=self.logger)
        session_key = splunk_ctx.authtoken
        system_key = splunk_ctx.system_authtoken

        try:
            # Best-effort cleanup of all product stanzas/tokens before resetting general state.
            # Do not fail disconnect if a single product cleanup fails.
            self.logger.info("Deleting product connections")
            product_stanzas = get_product_config(
                session_key=system_key,
                logger=self.logger,
            )

            # Collect known product family realms. Products in the same identity
            # family share a keypair and access token, so deduplicate by realm.
            family_realms_to_delete = set()
            for product_name in product_stanzas:
                product_family = get_product_family(product_name)
                if product_family is None:
                    self.logger.warning(
                        "Skipping secret cleanup for unknown cloud product: %s",
                        product_name,
                    )
                    continue
                family_realms_to_delete.add(product_family)

            for product_name, product_config in product_stanzas.items():
                product_status = product_config.get(PRODUCT_STATUS_KEY)
                self.logger.info(
                    "Cleaning up product %s (status=%s)", product_name, product_status
                )

                try:
                    # Remove product configuration from cloud-connection.conf
                    self._remove_product_from_config(
                        session_key=system_key,
                        cloud_product_name=product_name,
                    )
                except Exception as e:
                    self.logger.warning(
                        "Best-effort product cleanup failed (non-fatal): cloud_product_name=%s error=%s",
                        product_name,
                        e,
                        exc_info=True,
                    )

            # Delete keypairs and access tokens once per product family realm.
            for keypair_realm in family_realms_to_delete:
                try:
                    sm.delete_private_key_and_kid(
                        session_key=system_key, realm=keypair_realm
                    )
                    self.logger.info(
                        "Successfully removed keypair: realm=%s", keypair_realm
                    )
                except Exception as e:
                    self.logger.warning(
                        "Best-effort keypair cleanup failed (non-fatal): realm=%s error=%s",
                        keypair_realm,
                        e,
                    )
                try:
                    sm.delete_secret(
                        session_key=system_key,
                        realm=keypair_realm,
                        key_name=SP_ACCESS_TOKEN_SECRET_NAME,
                    )
                    self.logger.info(
                        "Successfully removed access token: realm=%s", keypair_realm
                    )
                except Exception as e:
                    self.logger.warning(
                        "Best-effort access token cleanup failed (non-fatal): realm=%s error=%s",
                        keypair_realm,
                        e,
                    )
        except Exception as e:
            self.logger.warning(
                "Best-effort product cleanup failed during discovery/iteration (non-fatal): error=%s",
                e,
                exc_info=True,
            )

        try:
            self.logger.info("Deleting cloud connection")

            # Reset all fields in the general stanza to default values
            default_values = {
                "tenantName": "",
                "region": "",
                "spID": "",
                "bootstrapLicenseID": "",
                "connectionState": CONNECTION_STATE_DISABLED,
                "deploymentId": "",
                "otpCreationTs": "",
                "otpExpirySeconds": "",
                "otpEmail": "",
                "lastKeyRotationTimestamp": "",
                "rotationInterval": "90",
                "tenantApiHostname": "",
                "pop": "",
                "regionAuthHostname": "",
                "requestedTenantName": "",
            }

            conf_path = SPLUNK_CLOUD_CONNECTION_CONF_URI

            resp, content = SCSUtils.simple_request_with_retry(
                self.logger,
                method="POST",
                path=conf_path,
                session_key=system_key,
                postargs=default_values,
            )

            status = getattr(resp, "status", None) if resp else None

            if status not in (200, 201):
                self.logger.error(
                    "Failed to reset cloud connection configuration. status=%s",
                    status or "n/a",
                )
                return DeleteCloudConnectionResponseBuilder.internal_server_error()

            # Delete the bootstrap SP access token (non-fatal)
            try:
                sm.delete_secret(
                    session_key=system_key,
                    realm=APP_NAME,
                    key_name=SP_ACCESS_TOKEN_SECRET_NAME,
                )
                self.logger.info("Successfully deleted bootstrap SP access token")
            except Exception as e:
                self.logger.warning(
                    "Failed to delete bootstrap SP access token (non-fatal): %s", e
                )

            # Delete the bootstrap SP private key and kid (non-fatal)
            try:
                sm.delete_private_key_and_kid(
                    session_key=system_key,
                    realm=APP_NAME,
                )
                self.logger.info(
                    "Successfully deleted bootstrap SP private key and kid"
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to delete bootstrap SP private key and kid (non-fatal): %s",
                    e,
                )

            CloudConnectionEventLog(session_key, self.logger).log(
                operation=OPERATION_DELETE_CLOUD_CONNECTION,
                event_type=AUDIT_EVENT_CLOUD_CONNECTION_DELETED,
                severity=AUDIT_SEVERITY_INFO,
            )

            self.logger.info("Successfully deactivated cloud connection")
            return DeleteCloudConnectionResponseBuilder.no_content()

        except Exception as e:
            self.logger.error("Error deleting cloud connection: %s", e)
            return DeleteCloudConnectionResponseBuilder.internal_server_error()

    @_require_capability(CAPABILITY_EDIT_CLOUD_CONNECTION)
    def create_cloud_connection_intake(
        self, splunk_ctx: SplunkContext, request: OnboardingConfig
    ) -> CreateCloudConnectionIntakeResponseBuilder:
        """
        POST /v1alpha1/cloud-connection/activate - Initiate cloud connection onboarding

        Args:
            request: OnboardingConfig with region, otpEmail, and requestedTenantName

        Returns:
            CreateCloudConnectionIntakeResponseBuilder indicating acceptance
        """
        try:
            # Validate that requestedTenantName does not start with "region-"
            # (reserved for SCS infrastructure hostnames)
            if request.requested_tenant_name.startswith("region-"):
                self.logger.warning(
                    "Rejected tenant name with reserved prefix: %s",
                    request.requested_tenant_name
                )
                return CreateCloudConnectionIntakeResponseBuilder.bad_request()
            
            self.logger.info(
                "Initiating cloud connection onboarding: "
                "region=%s, email=%s, requestedTenantName=%s",
                request.region,
                request.otp_email,
                request.requested_tenant_name,
            )
            session_key = splunk_ctx.authtoken
            system_key = splunk_ctx.system_authtoken
            user = splunk_ctx.user

            # Get all available license GUIDs
            license_guids = get_all_license_guids(system_key, self.logger)
            if not license_guids:
                return CreateCloudConnectionIntakeResponseBuilder.internal_server_error(
                    Error(
                        message="No valid matching license found for bootstrapping. "
                        "Ensure at least one valid license is installed on this instance."
                    )
                )

            # Get the hostname and deployment ID once (same for all attempts)
            hostname = socket.gethostname()
            self.logger.info("Retrieved hostname: %s", hostname)

            # Get the deployment ID — shcluster id for SHC, server/info guid for standalone
            deployment_id = SearchHeadUnit.get_deployment_id(self.logger, system_key)
            if not deployment_id:
                return CreateCloudConnectionIntakeResponseBuilder.internal_server_error(
                    Error(message="Unable to get deployment ID")
                )

            # Commerce OTP intake API requires lowercase GUIDs
            license_guids_lower = [guid.lower() for guid in license_guids]
            self.logger.info(
                "Sending %d license GUID(s) to Commerce OTP intake API: %s",
                len(license_guids_lower),
                license_guids_lower,
            )

            # Send all license GUIDs to Commerce OTP intake API in a single request
            response = self._request_otp_from_commerce(
                session_key=system_key,
                user=user,
                license_ids=license_guids_lower,
                tenant=request.requested_tenant_name,
                region=request.region,
                email=request.otp_email,
                deployment_id=str(deployment_id),
                hostname=hostname,
            )

            # Check response
            if not response or not response.ok:
                status_code = getattr(response, "status_code", None)
                self.logger.error(
                    "Commerce OTP intake API request failed. Response: status=%s, body=%s",
                    status_code,
                    getattr(response, "content", "None"),
                )

                # Return appropriate error based on Commerce API response
                if status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    return (
                        CreateCloudConnectionIntakeResponseBuilder.too_many_requests()
                    )
                elif status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
                    return (
                        CreateCloudConnectionIntakeResponseBuilder.unprocessable_entity()
                    )
                elif status_code == HTTPStatus.FORBIDDEN:
                    return CreateCloudConnectionIntakeResponseBuilder.forbidden()
                elif status_code == HTTPStatus.NOT_FOUND:
                    return CreateCloudConnectionIntakeResponseBuilder.not_found()

                # For any other error status (401, 500, 503, None, etc.), return service unavailable
                # Note: 401 is unexpected since the OTP intake endpoint is unauthenticated
                return CreateCloudConnectionIntakeResponseBuilder.service_unavailable()

            # Parse OTP response (only reached if response.ok is True)
            try:
                response_data = json.loads(response.content)
                otp_expiry = response_data.get("expiresInSeconds", 0)
                # Extract accepted licenseId from Commerce OTP intake API response
                bootstrap_license_guid = response_data.get("licenseId")
                if not bootstrap_license_guid:
                    self.logger.error(
                        "Commerce OTP intake API did not return licenseId in response"
                    )
                    return CreateCloudConnectionIntakeResponseBuilder.internal_server_error(
                        Error(message="Unable to get bootstrap license ID")
                    )
                self.logger.info(
                    "Commerce OTP intake API returned accepted licenseId: %s",
                    bootstrap_license_guid,
                )
            except (json.JSONDecodeError, AttributeError) as e:
                self.logger.error("Failed to parse OTP response JSON: %s", e)
                return CreateCloudConnectionIntakeResponseBuilder.internal_server_error(
                    Error(message="Failed to parse OTP response JSON")
                )
            current_timestamp = int(time.time())

            # Write tenant name, region, OTP expiry, and timestamp to cloud-connection.conf via splunkd API
            self.logger.info(
                "Writing configuration to cloud-connection.conf: "
                "requestedTenantName=%s, region=%s, otpExpiry=%s, timestamp=%s",
                request.requested_tenant_name,
                request.region,
                otp_expiry,
                current_timestamp,
            )

            # Read the current state before writing so we can detect real transitions.
            # If the stanza does not exist yet (first call) treat the previous state as
            # None — that is always a genuine transition to otp-requested.
            # Any failure here (missing stanza, transient splunkd error, parse error)
            # defaults to None so the telemetry-only read can never break onboarding.
            try:
                prev_config = get_cloud_connection_config(system_key, self.logger)
                prev_state = prev_config.get("connectionState")
            except Exception:
                prev_state = None

            try:
                self._update_connection_state(
                    session_key=system_key,
                    connection_state=CONNECTION_STATE_OTP_REQUESTED,
                    requestedTenantName=request.requested_tenant_name,
                    region=request.region,
                    bootstrapLicenseID=bootstrap_license_guid,
                    otpCreationTs=str(current_timestamp),
                    otpExpirySeconds=str(otp_expiry),
                    otpEmail=request.otp_email,
                    deploymentId=str(deployment_id),  # UUID.str() is infallible
                )
            except Exception as e:
                self.logger.error(
                    "Failed to write configuration to cloud-connection.conf: %s", e
                )
                return CreateCloudConnectionIntakeResponseBuilder.internal_server_error(
                    Error(
                        message="Failed to write configuration. See logs for more details."
                    )
                )

            self.logger.info(
                "Successfully wrote configuration to cloud-connection.conf"
            )

            # Emit AUDIT_EVENT_CONNECTION_STATE_CHANGED only when the state actually
            # transitions.  On OTP resend retries the state is already
            # otp-requested, so no transition event should be recorded.
            if prev_state != CONNECTION_STATE_OTP_REQUESTED:
                CloudConnectionEventLog(session_key, self.logger).log(
                    operation=OPERATION_CREATE_CLOUD_CONNECTION_INTAKE,
                    event_type=AUDIT_EVENT_CONNECTION_STATE_CHANGED,
                    severity=AUDIT_SEVERITY_INFO,
                )
            CloudConnectionEventLog(session_key, self.logger).log(
                operation=OPERATION_CREATE_CLOUD_CONNECTION_INTAKE,
                event_type=AUDIT_EVENT_OTP_REQUESTED,
                severity=AUDIT_SEVERITY_INFO,
            )

            return CreateCloudConnectionIntakeResponseBuilder.accepted(
                OnboardingInitiated.from_dict(
                    {
                        "hostname": hostname,
                        "deploymentId": str(deployment_id),  # UUID.str() is infallible
                        "requestedTenantName": request.requested_tenant_name,
                        "otpCreationTs": current_timestamp,
                        "otpExpirySeconds": otp_expiry,
                    }
                )
            )

        except Exception as e:
            self.logger.error("Error creating cloud connection intake: %s", e)
            return CreateCloudConnectionIntakeResponseBuilder.internal_server_error(
                Error(
                    message="Failed to create cloud connection. See logs for more details."
                )
            )

    def request_cloud_connection_otp(
        self, splunk_ctx: SplunkContext
    ) -> RequestCloudConnectionOTPResponseBuilder:
        """
        POST /v1alpha1/cloud-connection/otp-request - Create new OTP for cloud connection verification

        Triggers resend of OTP email. Reuses the parameters already stored in cloud-connection.conf.

        Returns:
            RequestCloudConnectionOTPResponseBuilder (202 on success).
        """
        try:
            self.logger.info("Resending OTP for cloud connection")
            session_key = splunk_ctx.authtoken
            system_key = splunk_ctx.system_authtoken
            user = splunk_ctx.user

            # Read current config from cloud-connection.conf
            resp, content = SCSUtils.simple_request_with_retry(
                self.logger,
                method="GET",
                path=SPLUNK_CLOUD_CONNECTION_CONF_URI,
                session_key=system_key,
                getargs={"output_mode": "json"},
            )
            status = getattr(resp, "status", None) if resp else None

            if status not in (200, 201):
                if status == 404:
                    self.logger.info(
                        "No cloud connection configuration found for OTP resend"
                    )
                    return RequestCloudConnectionOTPResponseBuilder.not_found()
                else:
                    self.logger.error(
                        "Failed to read cloud-connection.conf for OTP resend, status=%s",
                        status or "n/a",
                    )
                    return (
                        RequestCloudConnectionOTPResponseBuilder.internal_server_error()
                    )

            config_data = json.loads(content)
            entry = config_data.get("entry", [{}])[0]
            content_dict = entry.get("content", {})
            connection_state = content_dict.get("connectionState", "")

            if connection_state != CONNECTION_STATE_OTP_REQUESTED:
                self.logger.info(
                    "OTP resend not allowed: connection state is %s (expected otp-requested)",
                    connection_state,
                )
                return RequestCloudConnectionOTPResponseBuilder.internal_server_error()

            tenant_name = content_dict.get("requestedTenantName", "").strip()
            region = content_dict.get("region", "").strip()
            otp_email = content_dict.get("otpEmail", "").strip()
            deployment_id = content_dict.get("deploymentId", "").strip()
            if not all([tenant_name, region, otp_email, deployment_id]):
                self.logger.error(
                    "Missing required config for OTP resend: tenantName=%s, region=%s, "
                    "otpEmail=%s, deploymentId=%s",
                    tenant_name or "(missing)",
                    region or "(missing)",
                    otp_email or "(missing)",
                    deployment_id or "(missing)",
                )
                return RequestCloudConnectionOTPResponseBuilder.bad_request()

            # Use stored bootstrapLicenseID (commerce accepted GUID)
            bootstrap_license_id = (
                content_dict.get("bootstrapLicenseID") or ""
            ).strip()

            otp_creation_ts = None
            otp_creation_ts_raw = content_dict.get("otpCreationTs")
            if otp_creation_ts_raw is not None:
                try:
                    otp_creation_ts = int(otp_creation_ts_raw)
                except (TypeError, ValueError):
                    pass

            hostname = socket.gethostname()

            # Use stored bootstrapLicenseID for OTP resend
            if not bootstrap_license_id:
                self.logger.error(
                    "No bootstrapLicenseID found in config for OTP resend"
                )
                return RequestCloudConnectionOTPResponseBuilder.internal_server_error()

            self.logger.info(
                "Using stored bootstrapLicenseID for OTP resend: %s",
                bootstrap_license_id,
            )
            license_guids_lower = [bootstrap_license_id.lower()]

            response = self._request_otp_from_commerce(
                session_key=system_key,
                user=user,
                license_ids=license_guids_lower,
                tenant=tenant_name,
                region=region,
                email=otp_email,
                deployment_id=deployment_id,
                hostname=hostname,
                otp_creation_ts=otp_creation_ts,
            )

            if not response.ok:
                if (
                    getattr(response, "status_code", None)
                    == HTTPStatus.TOO_MANY_REQUESTS
                ):
                    return RequestCloudConnectionOTPResponseBuilder.too_many_requests()
                self.logger.info(
                    "Commerce OTP resend API request failed: status=%s, body=%s",
                    response.status_code,
                    response.content,
                )
                return RequestCloudConnectionOTPResponseBuilder.internal_server_error()

            try:
                response_data = json.loads(response.content)
                otp_expiry = response_data.get("expiresInSeconds", 0)
                accepted_license_id = response_data.get("licenseId")
            except (json.JSONDecodeError, AttributeError) as e:
                self.logger.error("Failed to parse OTP resend response JSON: %s", e)
                return RequestCloudConnectionOTPResponseBuilder.internal_server_error()
            current_timestamp = int(time.time())

            # Update config with OTP timestamps and accepted licenseId
            update_params = {
                "session_key": system_key,
                "connection_state": CONNECTION_STATE_OTP_REQUESTED,
                "otpCreationTs": str(current_timestamp),
                "otpExpirySeconds": str(otp_expiry),
            }
            if accepted_license_id:
                update_params["bootstrapLicenseID"] = accepted_license_id

            try:
                self._update_connection_state(**update_params)
            except Exception as e:
                self.logger.error(
                    "Failed to update cloud-connection.conf after OTP resend: %s", e
                )
                # Since we did actually succeed in re-sending the OTP, we don't return an error
                return RequestCloudConnectionOTPResponseBuilder.accepted()

            self.logger.info(
                "OTP resend completed successfully for tenant=%s", tenant_name
            )
            return RequestCloudConnectionOTPResponseBuilder.accepted()
        except Exception as e:
            self.logger.error("Error resending cloud connection OTP: %s", e)
            return RequestCloudConnectionOTPResponseBuilder.internal_server_error()

    @_require_capability(CAPABILITY_EDIT_CLOUD_CONNECTION)
    def create_cloud_connection(
        self, splunk_ctx: SplunkContext, request: OTPVerification
    ) -> CreateCloudConnectionResponseBuilder:
        """
        POST /v1alpha1/cloud-connection/verify - Verify OTP and establish connection

        Completes the cloud connection activation by verifying the OTP.
        This is the second step of the two-step activation process.

        Steps:
        1. Accept OTP payload as input
        2. Generate a public/private keypair for Bootstrap Service Principal ID
        3. Invoke CreateCloudConnection API to establish trust
        4. Commerce API is unauthenticated but payload has OTP for trust
        5. Persist private key in passwords.conf
        6. Poll Commerce endpoint to ensure connection is bootstrapped
        7. Update connection_state

        Args:
            request: OTPVerification with the OTP code (UUID format)
            session_key: Splunk session key for API calls

        Returns:
            CreateCloudConnectionResponseBuilder with appropriate status
        """
        try:
            # Step 1: Accept and validate OTP payload (done by handler)
            otp = str(request.otp)
            self.logger.info("Processing OTP verification request")
            session_key = splunk_ctx.authtoken
            system_key = splunk_ctx.system_authtoken

            # Retrieve stored onboarding configuration from cloud-connection.conf
            try:
                connection_config = get_cloud_connection_config(system_key, self.logger)
            except CloudConnectionConfigNotFoundError:
                return CreateCloudConnectionResponseBuilder.not_found()
            except ValueError:
                self.logger.error("Failed to parse configuration")
                return CreateCloudConnectionResponseBuilder.internal_server_error()

            # Check if connection already verified
            connection_state = connection_config.get("connectionState")
            if connection_state in [
                CONNECTION_STATE_IN_PROGRESS,
                CONNECTION_STATE_ENABLED,
            ]:
                self.logger.warning(
                    "Connection already verified (state: %s)", connection_state
                )
                return CreateCloudConnectionResponseBuilder.conflict()

            # Extract configuration details
            requested_tenant_name = connection_config.get("requestedTenantName")
            customer_region = connection_config.get("region")
            bootstrap_license_id = connection_config.get("bootstrapLicenseID").lower()

            if not all([requested_tenant_name, customer_region, bootstrap_license_id]):
                self.logger.error("Incomplete onboarding configuration")
                return CreateCloudConnectionResponseBuilder.internal_server_error()

            # Step 2: Generate ECDSA P-256 keypair for Bootstrap Service Principal
            self.logger.info("Generating public/private keypair for sending to scs")
            try:
                private_key = SCSUtils.generate_ecdsa_private_key(self.logger)
                public_key = SCSUtils.derive_ecdsa_public_key(self.logger, private_key)
            except Exception:
                self.logger.error("Failed to generate keypair")
                return CreateCloudConnectionResponseBuilder.internal_server_error()

            # Step 3: Build JWK from public key
            deployment_id = SearchHeadUnit.get_deployment_id(self.logger, system_key)
            if deployment_id is None:
                self.logger.error("Failed to retrieve deployment ID")
                return CreateCloudConnectionResponseBuilder.internal_server_error()
            issuer_id = str(deployment_id)
            # At onboarding the SP does not exist yet; use the issuer ID as the
            # kid prefix so the key can be registered before an spID is assigned.
            kid = SCSUtils.build_kid_from_issuer_id(issuer_id)
            try:
                jwk = SCSUtils.create_ecdsa_jwk(public_key=public_key, kid=kid)
            except Exception:
                self.logger.error("Failed to create JWK")
                return CreateCloudConnectionResponseBuilder.internal_server_error()

            # Step 4: Invoke CreateCloudConnection API call to establish trust
            # Commerce API is unauthenticated but payload has the OTP which establishes trust
            self.logger.info("Calling Commerce API to establish trust")
            try:
                commerce_response = self._call_commerce_create_connection(
                    session_key=system_key,
                    otp=otp,
                    license_id=bootstrap_license_id,
                    issuer_id=issuer_id,
                    issuer_public_key=jwk,
                )

                if not commerce_response.get("success"):
                    error_code = commerce_response.get("error_code")
                    if error_code == "OTP_EXPIRED":
                        return CreateCloudConnectionResponseBuilder.gone()
                    elif error_code == "OTP_INVALID":
                        return CreateCloudConnectionResponseBuilder.bad_request()
                    elif error_code == "RATE_LIMITED":
                        return CreateCloudConnectionResponseBuilder.too_many_requests()
                    else:
                        return (
                            CreateCloudConnectionResponseBuilder.service_unavailable()
                        )

                # Parse the response data
                response_data = commerce_response.get("data", {})
                sp_id = response_data.get("spID")
                tenant_name = response_data.get("tenant")
                tenant_hostname = response_data.get("tenantHostname")
                region_hostname = response_data.get("regionHostname")
                region_auth_hostname = response_data.get("regionAuthHostname")
                scs_region = response_data.get("region")

                self.logger.info(
                    "Successfully created cloud connection: "
                    "spID=%s, tenant=%s, tenantHostname=%s, regionHostname=%s, regionAuthHostname=%s, region=%s",
                    sp_id,
                    tenant_name,
                    tenant_hostname,
                    region_hostname,
                    region_auth_hostname,
                    scs_region,
                )

            except Exception:
                self.logger.error("Failed to call Commerce API")
                return CreateCloudConnectionResponseBuilder.service_unavailable()

            # Update connection state to in-progress
            self._update_connection_state(
                system_key,
                CONNECTION_STATE_IN_PROGRESS,
                sp_id,
                tenant_hostname,
                region_auth_hostname,
                tenantName=tenant_name,
                pop=scs_region,
            )
            CloudConnectionEventLog(session_key, self.logger).log(
                operation=OPERATION_CREATE_CLOUD_CONNECTION,
                event_type=AUDIT_EVENT_CONNECTION_STATE_CHANGED,
                severity=AUDIT_SEVERITY_INFO,
            )

            if not scs_region:
                self.logger.error(
                    "Commerce response missing region field, regionHostname=%s",
                    region_hostname,
                )
                return CreateCloudConnectionResponseBuilder.internal_server_error()

            # Step 5: Persist private key and kid in passwords.conf for cloud-connected app
            self.logger.info("Persisting private key and kid in passwords.conf")
            try:
                self._store_private_key_and_kid(system_key, private_key, kid)
            except Exception:
                self.logger.error("Failed to store private key and kid")
                return CreateCloudConnectionResponseBuilder.internal_server_error()

            # Generate access token for the service principal for polling call
            self.logger.info("Generating access token for the service principal")
            try:
                access_token = SCSUtils.create_principal_access_token(
                    logger=self.logger,
                    session_key=system_key,
                    splunk_user="system",
                    principal_id=sp_id,
                    kid=kid,
                    private_key=private_key,
                    tenant_name="system",
                    scope="system",
                )
            except Exception as e:
                self.logger.error("Failed to generate access token: %s", e)
                return CreateCloudConnectionResponseBuilder.internal_server_error()

            # Step 6: Poll Commerce endpoint to ensure connection is established
            self.logger.info("Polling Commerce API for connection establishment")
            polling_status = "timeout"  # Default to timeout in case of exception
            try:
                polling_status = self._poll_commerce_bootstrap_status(
                    session_key=system_key,
                    tenant_name=tenant_name,
                    access_token=access_token,
                    scs_region=scs_region,
                )
            except Exception as e:
                self.logger.warning("Error polling connection status: %s", e)
                # Non-fatal - connection may still establish

            # Step 7: Update connection_state based on polling result
            # Set to 'enabled' only if connection is active, otherwise 'in-progress'
            if polling_status == "active":
                new_state = CONNECTION_STATE_ENABLED
            else:
                new_state = CONNECTION_STATE_CREATE_FAILED

            self.logger.info("Updating connection state to: %s", new_state)
            try:
                # Update cloud-connection.conf with all relevant fields
                self._update_connection_state(
                    session_key=system_key,
                    connection_state=new_state,
                    sp_id=sp_id,
                    tenant_api_hostname=tenant_hostname,
                    region_auth_hostname=region_auth_hostname,
                    pop=scs_region,
                )
                CloudConnectionEventLog(session_key, self.logger).log(
                    operation=OPERATION_CREATE_CLOUD_CONNECTION,
                    event_type=AUDIT_EVENT_CONNECTION_STATE_CHANGED,
                    severity=AUDIT_SEVERITY_INFO,
                )
            except Exception as e:
                self.logger.error("Failed to update connection state: %s", e)
                # Non-fatal - connection was established on commerce side

            if new_state == CONNECTION_STATE_ENABLED:
                CloudConnectionEventLog(session_key, self.logger).log(
                    operation=OPERATION_CREATE_CLOUD_CONNECTION,
                    event_type=AUDIT_EVENT_CLOUD_CONNECTION_CREATED,
                    severity=AUDIT_SEVERITY_INFO,
                )

            self.logger.info("OTP verification completed successfully")
            return CreateCloudConnectionResponseBuilder.accepted()

        except Exception as e:
            self.logger.error(
                "Unexpected error in create_cloud_connection: %s", e, exc_info=True
            )
            return CreateCloudConnectionResponseBuilder.internal_server_error()

    # ========== Private Helper Methods ==========
    def _store_private_key_and_kid(
        self, session_key: str, private_key: str, kid: str
    ) -> None:
        """
        Store private key and kid in passwords.conf for the cloud-connected app.

        Uses SecretManager to securely store both the private key and key identifier
        as a single JSON payload in the service principal's realm.

        Args:
            session_key: Splunk session key for authentication
            private_key: The private key in PEM format to store
            kid: Key identifier
        Raises:
            Exception: If storage fails
        """
        try:
            secret_manager = SecretManager(logger=self.logger)

            secret_manager.upsert_private_key_and_kid(
                session_key=session_key,
                realm=APP_NAME,
                private_key_pem=private_key,
                kid=kid,
            )

            self.logger.info(
                "Successfully stored private key and kid in passwords.conf"
            )

        except Exception as e:
            self.logger.error("Error storing private key and kid: %s", e)
            raise

    def _call_commerce_create_connection(
        self,
        session_key: str,
        otp: str,
        license_id: str,
        issuer_id: str,
        issuer_public_key: dict,
    ) -> dict:
        """
        Call Commerce API to create cloud connection with OTP verification.

        The Commerce API is unauthenticated but the OTP in the payload establishes trust.

        Args:
            session_key: Splunk session key for proxy configuration
            otp: One-time password for verification
            license_id: License identifier (bootstrap license ID)
            issuer_id: Issuer identifier (deployment ID)
            issuer_public_key: JSON Web Key containing public key with fields:
                - kty: Key type (e.g., "EC")
                - kid: Key identifier
                - crv: Curve (e.g., "P-256")
                - alg: Algorithm (e.g., "ES256")
                - x: X coordinate (base64url encoded)
                - y: Y coordinate (base64url encoded)

        Returns:
            dict with:
                - 'success': boolean indicating if request succeeded
                - 'error_code': optional error code if failed
                - 'data': optional response data if succeeded, containing:
                    - spID: Service Principal ID
                    - tenant: Tenant name
                    - tenantHostname: Tenant hostname
                    - regionHostname: Region hostname
        """
        # Using staging URL for OTP verification
        # Once tenant-based routing is needed, pass tenant_name to the function
        url = get_commerce_api_uri_cloud_connection(session_key)

        payload = {
            "licenseId": license_id,
            "otp": otp,
            "issuerID": issuer_id,
            "issuerPublicKey": issuer_public_key,
        }

        try:
            # this call isn't idempotent; we cannot retry sending
            # the same otp in case of high network latency (otp gets used up)
            # so we set high read timeout with no retry
            resp = tracked_request_with_splunkd_proxy(
                session_key=session_key,
                logger=self.logger,
                operation=OPERATION_CREATE_CLOUD_CONNECTION,
                method="POST",
                url=url,
                splunk_user="system",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=SCSUtils._get_connection_config(self.logger, session_key)[
                    "long_timeout"
                ],
                retry_read=0,
            )

            status_code = getattr(resp, "status_code", None)

            if (
                status_code == http.client.CREATED
                or status_code == http.client.ACCEPTED
                or status_code == http.client.OK
            ):
                # Parse the response body
                try:
                    response_data = resp.json()
                    return {"success": True, "data": response_data}
                except Exception as parse_error:
                    self.logger.error(
                        "Failed to parse Commerce API response: %s", parse_error
                    )
                    return {"success": False, "error_code": "PARSE_ERROR"}
            elif status_code == http.client.GONE:
                return {"success": False, "error_code": "OTP_EXPIRED"}
            elif status_code == http.client.BAD_REQUEST:
                return {"success": False, "error_code": "OTP_INVALID"}
            elif status_code == http.client.TOO_MANY_REQUESTS:
                self.logger.warning("Commerce API rate limiting (429)")
                return {"success": False, "error_code": "RATE_LIMITED"}
            else:
                self.logger.error(
                    "Commerce API returned unexpected status: %s %s",
                    status_code,
                    resp.content,
                )
                return {"success": False, "error_code": "UNKNOWN"}

        except Exception as e:
            self.logger.error("Error calling Commerce API: %s", e)
            raise

    def _poll_commerce_bootstrap_status(
        self, session_key: str, tenant_name: str, access_token: str, scs_region: str
    ) -> str:
        """
        Poll Commerce endpoint to check if connection is established.

        Polls the Commerce API until the 'connection_established' field is either
        'active' (success) or 'failed' (failure), or until the timeout is reached.

        Polls for 30 minutes at 10-second intervals (180 total attempts); worst case
        should be about 20 minutes. If a 429 (rate limited) response is received,
        doubles the interval for backoff.

        Args:
            session_key: Splunk session key for proxy configuration
            tenant_name: Tenant name to query
            access_token: Access token for the service principal
        Returns:
            str where:
                - 'active' if successful, 'failed' if connection failed,
                         'timeout' if polling timed out
        """
        # Poll for 30 minutes at 10-second intervals
        max_timeout = 1800  # 30 minutes
        initial_interval = 10  # 10 seconds
        current_interval = initial_interval

        url = get_uri_cloud_connection_config(tenant_name, scs_region, session_key)
        start_time = time.time()
        attempt = 0

        self.logger.info(
            "Starting connection bootstrap polling to %s (max %d seconds, initial interval %d seconds)",
            url,
            max_timeout,
            initial_interval,
        )

        while True:
            attempt += 1
            elapsed_time = time.time() - start_time

            # Check if we've exceeded max poll time
            if elapsed_time >= max_timeout:
                self.logger.warning(
                    "Connection establishment polling timed out after %d seconds (%d attempts). "
                    "The connection may still establish later.",
                    int(elapsed_time),
                    attempt,
                )
                return "timeout"

            try:
                self.logger.info(
                    "Polling connection status (attempt %d, elapsed %ds)",
                    attempt,
                    int(elapsed_time),
                )

                response = tracked_request_with_splunkd_proxy(
                    session_key=session_key,
                    logger=self.logger,
                    operation=OPERATION_CREATE_CLOUD_CONNECTION,
                    method="GET",
                    url=url,
                    params={"output_mode": "json"},
                    splunk_user="system",
                    access_token=access_token,
                )

                status_code = response.status_code

                if status_code == http.client.OK:
                    try:
                        data = response.json()
                        connection_established = data.get(
                            "connection_established", ""
                        ).lower()

                        self.logger.debug(
                            "Connection status: %s", connection_established
                        )

                        if connection_established == "active":
                            self.logger.info(
                                "Connection successfully established (attempt %d, elapsed %ds)",
                                attempt,
                                int(elapsed_time),
                            )
                            return "active"
                        elif connection_established == "failed":
                            self.logger.error(
                                "Connection establishment failed on Commerce side. "
                                "The connection reported a failure status. %s",
                                data,
                            )
                            return "failed"
                        else:
                            # Still inactive or other status, continue polling
                            self.logger.debug(
                                "Connection not yet established (status: %s), "
                                "will retry in %d seconds...",
                                connection_established,
                                current_interval,
                            )
                    except json.JSONDecodeError as e:
                        self.logger.warning("Failed to parse JSON response: %s", e)
                    except Exception as e:
                        self.logger.warning(
                            "Error parsing connection status response: %s", e
                        )

                elif status_code == http.client.TOO_MANY_REQUESTS:
                    # Rate limited - double the interval for backoff
                    old_interval = current_interval
                    current_interval = min(current_interval * 2, max_timeout)
                    self.logger.warning(
                        "Rate limited (429) on attempt %d - increasing interval from %ds to %ds",
                        attempt,
                        old_interval,
                        current_interval,
                    )

                elif status_code == http.client.NOT_FOUND:
                    self.logger.warning(
                        "Connection config not found for tenant: %s", tenant_name
                    )
                else:
                    self.logger.warning(
                        "Unexpected status code from Commerce API: url=%s code=%s body=%s",
                        url,
                        status_code,
                        response.content,
                    )

            except Exception as e:
                self.logger.warning(
                    "Error polling connection status (attempt %d): %s", attempt, e
                )

            # Wait before next attempt (but not if we'd exceed max poll time)
            time_remaining = max_timeout - (time.time() - start_time)
            if time_remaining <= 0:
                self.logger.warning(
                    "Connection establishment polling timed out after %d seconds (%d attempts). "
                    "The connection may still establish later.",
                    int(time.time() - start_time),
                    attempt,
                )
                return "timeout"

            # Sleep for the interval or remaining time, whichever is less
            sleep_time = min(current_interval, time_remaining)
            time.sleep(sleep_time)

    def _update_connection_state(
        self,
        session_key: str,
        connection_state: str,
        sp_id: str = None,
        tenant_api_hostname: str = None,
        region_auth_hostname: str = None,
        **additional_fields,
    ) -> None:
        """
        Update the connection state in cloud-connection.conf.

        Args:
            session_key: Splunk session key for authentication
            connection_state: New connection state (e.g., 'in-progress', 'enabled')
            sp_id: Service Principal ID (optional)
            **additional_fields: Any additional fields to update

        Raises:
            Exception: If update fails
        """
        # Prepare update payload
        update_data = {"connectionState": connection_state}

        if sp_id:
            update_data["spID"] = sp_id

        if tenant_api_hostname:
            update_data["tenantApiHostname"] = tenant_api_hostname

        if region_auth_hostname:
            update_data["regionAuthHostname"] = region_auth_hostname

        # Add any additional fields
        update_data.update(additional_fields)

        try:
            resp, content = SCSUtils.simple_request_with_retry(
                logger=self.logger,
                method="POST",
                path=SPLUNK_CLOUD_CONNECTION_CONF_URI,
                session_key=session_key,
                postargs=update_data,
            )

            status = getattr(resp, "status", None) if resp else None
            if status not in (http.client.OK, http.client.CREATED):
                raise Exception("Failed to update connection state: status=%s" % status)

            self.logger.info(
                "Successfully updated connection state to: %s", connection_state
            )

        except Exception as e:
            self.logger.error("Error updating connection state: %s", e)
            raise

    def _check_scs_product_status(
        self,
        session_key: str,
        user: str,
        tenant: str,
        issuer_id: str,
        product_code: str,
        access_token: str,
        current_status: str,
    ) -> str:
        """
        Check the latest product status from SCS API.

        Uses the provided product-specific service principal access token to query SCS.

        Args:
            session_key: Splunk session key for authentication
            user: Splunk user for the request
            tenant: Tenant name
            issuer_id: Issuer ID (deployment ID)
            product_code: Product code for the cloud product
            access_token: Product-specific access token for SCS API call
            current_status: Current status from configuration

        Returns:
            Updated status from SCS, or current_status if check fails
        """
        try:
            # Get SCS product status URL
            product_url = get_commerce_api_uri_cloud_product_code(
                session_key, tenant, issuer_id, product_code
            )

            # Call SCS API to get current status
            response = tracked_request_with_splunkd_proxy(
                session_key=session_key,
                logger=self.logger,
                operation=OPERATION_GET_CLOUD_CONNECTION_PRODUCT,
                method="GET",
                url=product_url,
                splunk_user=user,
                access_token=access_token,
            )

            self.logger.info(
                'SCS status check response at url "%s": code=%s body=%s',
                product_url,
                response.status_code,
                response.content,
            )
            if response.status_code == http.client.OK:
                scs_data = response.json()
                api_status = scs_data.get("status")

                if api_status:
                    # Map API status to internal status
                    internal_status = CLOUD_PRODUCT_STATUS_REVERSE_MAPPING.get(
                        api_status
                    )

                    if internal_status is None:
                        # Unknown status from SCS - keep current status and log warning
                        self.logger.warning(
                            "Unknown status from SCS: api_status=%s, keeping current_status=%s, scs_response=%s",
                            api_status,
                            current_status,
                            scs_data,
                        )
                        return current_status

                    self.logger.info(
                        "Updated status from SCS: api_status=%s, internal_status=%s",
                        api_status,
                        internal_status,
                    )
                    return internal_status
            else:
                self.logger.warning(
                    "Failed to get status from SCS: status_code=%s",
                    response.status_code,
                )
        except Exception as e:
            self.logger.warning(
                "Failed to check SCS status (using config status): %s", e
            )

        return current_status

    def _update_product_status(
        self,
        session_key: str,
        cloud_product_name: str,
        status: str,
    ) -> None:
        """Persist the product status to cloud-connection.conf (non-fatal)."""
        try:
            product_stanza_name = f"{PRODUCT_STANZA_PREFIX}{cloud_product_name}"
            conf_path = f"/servicesNS/nobody/{APP_NAME}/configs/conf-cloud-connection/{product_stanza_name}"
            resp, content = SCSUtils.simple_request_with_retry(
                logger=self.logger,
                method="POST",
                path=conf_path,
                session_key=session_key,
                postargs={
                    PRODUCT_STATUS_KEY: status,
                },
            )
            resp_status = getattr(resp, "status", None)
            if resp_status not in (200, 201):
                self.logger.warning(
                    "Failed to persist product status=%s for %s, status_code=%s, body=%s",
                    status,
                    cloud_product_name,
                    resp_status,
                    content,
                )
            else:
                self.logger.info(
                    "Persisted product status=%s for %s", status, cloud_product_name
                )
        except Exception as e:
            self.logger.warning(
                "Failed to persist product status for %s: %s", cloud_product_name, e
            )

    def _request_otp_from_commerce(
        self,
        session_key: str,
        user: str,
        license_ids: List[str],
        tenant: str,
        region: str,
        email: str,
        deployment_id: str,
        hostname: str,
        otp_creation_ts: Optional[int] = None,
    ):
        """
        POST to the Commerce API OTP intake endpoint to send or resend an OTP email.

        When otp_creation_ts is provided, requires at least 2 minutes
        since that timestamp before making the request.

        Args:
            session_key: Splunk session key for authentication
            user: Splunk user for the request
            license_ids: List of license GUIDs (lowercase)
            tenant: Tenant name
            region: Region (e.g. us-east-1)
            email: Email address to receive the OTP
            deployment_id: Splunk deployment/instance GUID
            hostname: Splunk instance hostname (sent as sourceHint in payload for the email)
            otp_creation_ts: Optional Unix timestamp of last OTP creation

        Returns:
            The response object from request_with_splunkd_proxy (has .ok, .status_code,
            .content), or a response-like object with .ok=False, .status_code=429 when
            resend is rate-limited.
        """
        # fetch otp creation ts from cloud-connection.conf if not provided
        # mainly to prevent abuse of otp endpoint triggered by repeated intake requests
        if otp_creation_ts is None:
            resp, content = SCSUtils.simple_request_with_retry(
                self.logger,
                method="GET",
                path=SPLUNK_CLOUD_CONNECTION_CONF_URI,
                session_key=session_key,
                getargs={"output_mode": "json"},
            )
            status = getattr(resp, "status", None) if resp else None

            if status not in (200, 201):
                if status == 404:
                    self.logger.info(
                        "No cloud connection configuration found for OTP resend"
                    )
                    return SimpleNamespace(ok=False, status_code=404, content=b"")
                else:
                    self.logger.error(
                        "Failed to read cloud-connection.conf for OTP resend, status=%s",
                        status or "n/a",
                    )
                    return SimpleNamespace(ok=False, status_code=500, content=b"")

            config_data = json.loads(content)
            entry = config_data.get("entry", [{}])[0]
            content_dict = entry.get("content", {})

            otp_creation_ts_raw = content_dict.get("otpCreationTs")
            if otp_creation_ts_raw is not None:
                try:
                    otp_creation_ts = int(otp_creation_ts_raw)
                except (TypeError, ValueError):
                    pass

        # if otp_creation_ts, ensure at least 2 minutes have passed since last OTP creation
        # if not, should be a fresh trigger from intake and we can ignore 2 min check
        if otp_creation_ts is not None:
            elapsed_seconds = int(time.time()) - otp_creation_ts
            if elapsed_seconds < 120:
                self.logger.info(
                    "OTP request rejected: only %ds since last OTP (minimum 120s)",
                    elapsed_seconds,
                )
                return SimpleNamespace(ok=False, status_code=429, content=b"")

        return tracked_request_with_splunkd_proxy(
            session_key=session_key,
            logger=self.logger,
            operation=OPERATION_CREATE_CLOUD_CONNECTION_INTAKE,
            method="POST",
            url=get_commerce_api_uri_otp_intake(session_key),
            splunk_user=user,
            json={
                "licenseIds": license_ids,
                "tenant": tenant,
                "region": region,
                "email": email,
                "deploymentId": deployment_id,
                "sourceHint": hostname,
            },
        )

    @staticmethod
    def _parse_uuid(val: Any) -> Optional[UUID]:
        try:
            return UUID(val)
        except (ValueError, TypeError):
            return None

    @_require_capability(CAPABILITY_GET_CLOUD_CONNECTION_PRODUCT)
    def get_cloud_connection_product(
        self,
        splunk_ctx: SplunkContext,
        cloud_product_name: str,
    ) -> GetCloudConnectionProductResponseBuilder:
        """Return cloud-connection details for a specific cloud product.

        Returned Status codes:
        - 200: Cloud connection is enabled and the product stanza exists.
          Returns `CloudConnectionDetails` with:
          - `tenant`
          - `token` (optional; included only when the product status is 'activated')
          - `spID`
          - `status`
          - `licenseID`
          - `name`
          - `productCode`
        - 403: The operation isn't authorized (missing capability `license_edit`).
        - 404: Cloud connection is not enabled, or the product stanza does not exist.
        - 500: Required attributes are missing from configuration (e.g. `tenantName`,
          `licenseGUID`, `spID`, `cloudProductName`, `productCode`).

        Args:
            cloud_product_name: Cloud product identifier used to locate the product
                stanza (prefixed by `PRODUCT_STANZA_PREFIX`).
            session_key: Splunk session key used to authenticate REST calls.

        Returns:
            A `GetCloudConnectionProductResponseBuilder` containing either:
            - an OK response with `CloudConnectionDetails`, or
            - an error response describing why the details could not be returned.
        """
        session_key = splunk_ctx.authtoken
        system_key = splunk_ctx.system_authtoken
        user = splunk_ctx.user
        conf_entries = get_cloud_connection_conf_entries(
            logger=self.logger,
            session_key=system_key,
        )
        stanzas = self._find_general_and_product_stanzas(conf_entries)
        general: Dict[str, Any] = stanzas.get(CONFIG_STANZA)
        connection_state = (
            (general.get(GENERAL_CONNECTION_STATE_KEY) or "").strip().lower()
        )
        if connection_state != CONNECTION_STATE_ENABLED:
            self.logger.info(
                "Cloud connection is not enabled. connection_state=%s cloud_product_name=%s",
                connection_state,
                cloud_product_name,
            )
            return GetCloudConnectionProductResponseBuilder(
                Response(
                    http.client.NOT_FOUND,
                    json.dumps(
                        {
                            "message": "Cloud connection is not enabled",
                            "connection_state": connection_state,
                        }
                    ),
                    {"Content-Type": "application/json"},
                )
            )

        missing_fields: List[str] = []
        invalid_fields: List[str] = []
        tenant = general.get(GENERAL_TENANT_NAME_KEY)
        if not tenant:
            missing_fields.append(GENERAL_TENANT_NAME_KEY)

        product_content = stanzas.get(PRODUCT_STANZA_PREFIX + cloud_product_name)
        if not product_content:
            self.logger.info(
                "Cloud product not found in config. cloud_product_name=%s",
                cloud_product_name,
            )
            return GetCloudConnectionProductResponseBuilder(
                Response(
                    http.client.NOT_FOUND,
                    json.dumps(
                        {
                            "message": "Cloud product not found",
                            "cloud_product_name": cloud_product_name,
                        }
                    ),
                    {"Content-Type": "application/json"},
                )
            )

        status = product_content.get(PRODUCT_STATUS_KEY, "").strip().lower()

        # If activation failed, only the product name and status are available — skip field validation
        if status != CLOUD_PRODUCT_STATUS_ACTIVATION_FAILED:
            license_id_str = product_content.get(PRODUCT_LICENSE_GUID_KEY)
            if not license_id_str:
                missing_fields.append(PRODUCT_LICENSE_GUID_KEY)
                license_id = None
            else:
                license_id = self._parse_uuid(license_id_str)
                if not license_id:
                    invalid_fields.append(PRODUCT_LICENSE_GUID_KEY)

            sp_id = product_content.get(PRODUCT_SP_ID_KEY)
            if not sp_id:
                missing_fields.append(PRODUCT_SP_ID_KEY)

            product_code = product_content.get(PRODUCT_PRODUCT_CODE_KEY)
            if not product_code:
                missing_fields.append(PRODUCT_PRODUCT_CODE_KEY)

            product_name = product_content.get(PRODUCT_NAME_KEY)
            if not product_name:
                missing_fields.append(PRODUCT_NAME_KEY)
            elif product_name != cloud_product_name:
                invalid_fields.append(PRODUCT_NAME_KEY)

            if missing_fields or invalid_fields:
                self.logger.error(
                    "Missing or invalid required attributes. cloud_product_name=%s missing=%s invalid=%s",
                    cloud_product_name,
                    missing_fields,
                    invalid_fields,
                )
                payload: Dict[str, Any] = {
                    "message": "Missing or invalid required attributes in configuration",
                    "cloud_product_name": cloud_product_name,
                }
                if missing_fields:
                    payload["missing_fields"] = sorted(missing_fields)
                if invalid_fields:
                    payload["invalid_fields"] = sorted(invalid_fields)
                return GetCloudConnectionProductResponseBuilder(
                    Response(
                        http.client.INTERNAL_SERVER_ERROR,
                        json.dumps(payload),
                        {"Content-Type": "application/json"},
                    )
                )
        else:
            license_id = None
            sp_id = None
            product_code = None
            product_name = cloud_product_name

        # If status is not activated, check with SCS for the latest status
        # using the general/bootstrap SP access token.
        # Skip activation-failed: product_code is not available in conf when activation
        # fails, so _check_scs_product_status would query SCS with product_code=None.
        # Skip deactivated: product has been explicitly deactivated locally, no need to check SCS.
        if (
            status != CLOUD_PRODUCT_STATUS_ACTIVATED
            and status != CLOUD_PRODUCT_STATUS_ACTIVATION_FAILED
            and status != CLOUD_PRODUCT_STATUS_DEACTIVATED
        ):
            self.logger.info(
                "Cloud product is not activated and not activation-failed (status=%s). Checking SCS for latest status. cloud_product_name=%s tenant=%s",
                status,
                cloud_product_name,
                tenant,
            )

            try:
                # Get general/bootstrap SP access token for SCS status check
                general_sp_id = general.get(PRODUCT_SP_ID_KEY)
                general_access_token, _ = get_valid_access_token(
                    session_key=system_key,
                    realm=APP_NAME,
                    principal_id=general_sp_id,
                    tenant_name=tenant,
                    logger=self.logger,
                )

                # Get issuer ID (deployment ID) — non-fatal; fall through on failure
                deployment_id = SearchHeadUnit.get_deployment_id(
                    self.logger, system_key
                )
                if deployment_id is None:
                    raise RuntimeError("Failed to retrieve deployment ID")
                issuer_id = str(deployment_id)

                # Check SCS for latest status
                scs_status = self._check_scs_product_status(
                    session_key=system_key,
                    user=user,
                    tenant=tenant,
                    issuer_id=issuer_id,
                    product_code=product_code,
                    access_token=general_access_token,
                    current_status=status,
                )

                # If SCS reports a different status, persist it to conf
                if scs_status != status:
                    self._update_product_status(
                        session_key=system_key,
                        cloud_product_name=cloud_product_name,
                        status=scs_status,
                    )

                status = scs_status
            except Exception as e:
                # Non-fatal: continue with status from config
                self.logger.warning(
                    "Failed to check SCS status (using config status): %s", e
                )

        self.logger.info(
            "Returning cloud product status. cloud_product_name=%s status=%s",
            cloud_product_name,
            status,
        )

        if status == CLOUD_PRODUCT_STATUS_ACTIVATION_FAILED:
            return GetCloudConnectionProductResponseBuilder(
                Response(
                    http.client.OK,
                    json.dumps(
                        {
                            "name": cloud_product_name,
                            "status": status,
                        }
                    ),
                    {"Content-Type": "application/json"},
                )
            )

        details = CloudConnectionDetails(
            tenant_name=tenant,
            sp_id=sp_id,
            status=status,
            license_id=license_id,
            name=product_name,
            product_code=product_code,
            tenant_api_hostname=general.get("tenantApiHostname"),
        )

        # Include product-specific token in response if status is activated
        if status == CLOUD_PRODUCT_STATUS_ACTIVATED:
            try:
                product_family = get_product_family(product_name)
                if product_family is None:
                    raise RuntimeError(
                        "Unknown cloud product name: {}".format(product_name)
                    )
                access_token, _ = get_valid_access_token(
                    session_key=system_key,
                    realm=product_family,
                    principal_id=sp_id,
                    tenant_name=tenant,
                    logger=self.logger,
                )
                details.token = access_token
            except Exception as e:
                self.logger.error("Failed to get access token for product: %s", e)
                return GetCloudConnectionProductResponseBuilder(
                    Response(
                        http.client.INTERNAL_SERVER_ERROR,
                        json.dumps(
                            {
                                "message": "Failed to get access token",
                                "cloud_product_name": cloud_product_name,
                            }
                        ),
                        {"Content-Type": "application/json"},
                    )
                )

        return GetCloudConnectionProductResponseBuilder.ok(details)

    @_require_capability(CAPABILITY_GET_CLOUD_CONNECTION_PRODUCT)
    def get_cloud_connection_product_status(
        self,
        splunk_ctx: SplunkContext,
        cloud_product_name: str,
    ) -> GetCloudConnectionProductStatusResponseBuilder:

        cloud_connection_product = self.get_cloud_connection_product(
            splunk_ctx, cloud_product_name
        )
        cloud_connection_product_response = (
            cloud_connection_product.get_response() or {}
        )

        # If cloud connection details cannot be retrieved, return the same error response for the status endpoint
        if cloud_connection_product_response.status != http.client.OK:
            return cloud_connection_product

        # Filter out the status field from response body and return it in the response of this endpoint
        status = json.loads(cloud_connection_product_response.body).get("status")

        details = CloudConnectionStatus(
            status=status,
        )

        return GetCloudConnectionProductStatusResponseBuilder.ok(details)

    @staticmethod
    def _find_general_and_product_stanzas(
        entries: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        stanzas = {}
        for entry in entries:
            stanza_name = entry.get("name")
            if not isinstance(stanza_name, str) or not stanza_name:
                continue
            content = entry.get("content") or {}
            if not isinstance(content, dict):
                continue

            if stanza_name == CONFIG_STANZA or stanza_name.startswith(
                PRODUCT_STANZA_PREFIX
            ):
                stanzas[stanza_name] = content
        return stanzas

    def _remove_product_from_config(
        self, session_key: str, cloud_product_name: str
    ) -> None:
        """Delete a single product stanza from cloud-connection.conf."""
        product_stanza_name = f"{PRODUCT_STANZA_PREFIX}{cloud_product_name}"
        conf_path = f"/servicesNS/nobody/{APP_NAME}/configs/conf-cloud-connection/{product_stanza_name}"

        resp, _content = SCSUtils.simple_request_with_retry(
            logger=logger,
            method="DELETE",
            path=conf_path,
            session_key=session_key,
        )

        status_code = getattr(resp, "status", None)
        if status_code not in (
            http.client.OK,
            http.client.NO_CONTENT,
            http.client.NOT_FOUND,
        ):
            self.logger.error(
                "Failed to remove product from config: status=%s cloud_product_name=%s",
                status_code,
                cloud_product_name,
            )
            raise Exception(f"Failed to remove product from config: HTTP {status_code}")

        self.logger.info(
            "Successfully removed product from config: cloud_product_name=%s",
            cloud_product_name,
        )
