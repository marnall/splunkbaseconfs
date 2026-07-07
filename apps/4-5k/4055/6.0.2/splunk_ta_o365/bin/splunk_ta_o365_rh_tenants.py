#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import splunk_ta_o365_bootstrap
import sys
import json
import urllib.parse
import logging

import requests
from requests.packages import urllib3  # type: ignore
from solnlib import utils as sutils

from solnlib import conf_manager
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler.error import RestError
from splunktaucclib.rest_handler import admin_external, util, error
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunk_ta_o365.common.settings import Proxy, get_config_manager
from rh_common import CertThumbprintValidator

util.remove_http_proxy_env_vars()

APP_NAME = "splunk_ta_o365"

from splunk_ta_o365.common.utils import get_logger
from splunk_ta_o365.common.portal import O365LoginPortal

logger = get_logger("splunk_ta_o365_rest_handlers")

fields = [
    field.RestField(
        "endpoint", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "tenant_id",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[0-9a-fA-F]{8}(\-[0-9a-fA-F]{4}){3}\-[0-9a-fA-F]{12}$""",
        ),
    ),
    field.RestField(
        "client_id",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[0-9a-fA-F]{8}(\-[0-9a-fA-F]{4}){3}\-[0-9a-fA-F]{12}$""",
        ),
    ),
    field.RestField(
        "change_cert_creds", required=False, encrypted=False, default=0, validator=None
    ),
    field.RestField(
        "auth_type",
        required=True,
        encrypted=False,
        default="secret_based",
        validator=None,
    ),
    field.RestField(
        "cert_private_key", required=False, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "cert_thumbprint",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=128,
            min_len=1,
        ),
    ),
    field.RestField(
        "private_key_password",
        required=False,
        encrypted=True,
        default=None,
        validator=None,
    ),
    field.RestField(
        "change_client_secret",
        required=False,
        encrypted=False,
        default=0,
        validator=None,
    ),
    field.RestField(
        "client_secret", required=False, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "change_cas_secret", required=False, encrypted=False, default=0, validator=None
    ),
    field.RestField(
        "cloudappsecuritytoken",
        required=False,
        encrypted=True,
        default=None,
        validator=None,
    ),
    field.RestField(
        "cas_portal_url",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=63,
                min_len=1,
            ),
            validator.Pattern(
                regex=r"""^([A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?)$""",
            ),
        ),
    ),
    field.RestField(
        "cas_portal_data_center",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=63,
                min_len=1,
            ),
            validator.Pattern(
                regex=r"""^([A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?)$""",
            ),
        ),
    ),
]
model = RestModel(fields, name=None)

endpoint = SingleModel("splunk_ta_o365_tenants", model, config_name="tenants")


class TenantValidator:
    def __init__(
        self, session_key, tenant_name=None, updated_tenant=None, is_create=False
    ):
        self._session_key = session_key
        self._tenant_name = tenant_name
        self._updated_tenant = updated_tenant
        self._is_create = is_create

    def _response(self, status, data=None):
        if not data:
            data = {"status": status, "entry": []}
        payload = json.dumps(data)
        return {"status": status, "payload": payload}

    def _error(self, status, text=None, trace=None):
        payload = json.dumps(
            {"messages": [{"text": text, "type": "ERROR"}], "trace": trace}
        )
        return {"status": status, "payload": payload}

    def _convert(self, value):
        return value.encode("utf-8") if sys.version_info < (3,) else value

    def _get_conf_content(self, conf_name, stanza_name=None, is_creds_include=False):
        cfm = None
        if is_creds_include:
            cfm = conf_manager.ConfManager(
                self._session_key,
                APP_NAME,
                realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{conf_name}",
            )
        else:
            cfm = conf_manager.ConfManager(self._session_key, APP_NAME)

        conf = cfm.get_conf(conf_name)
        conf_content = conf.get(stanza_name=stanza_name, only_current_app=True)
        return conf_content

    def _load_existing_tenant(self, name):
        conf_name = "splunk_ta_o365_tenants"
        ext_tenant = self._get_conf_content(conf_name, name, is_creds_include=True)

        tenant = {
            "endpoint": ext_tenant.get("endpoint"),
            "tenant_id": ext_tenant.get("tenant_id"),
            "client_id": ext_tenant.get("client_id"),
            "auth_type": ext_tenant.get("auth_type"),
            "client_secret": ext_tenant.get("client_secret"),
            "cert_private_key": ext_tenant.get("cert_private_key"),
            "cert_thumbprint": ext_tenant.get("cert_thumbprint"),
            "private_key_password": ext_tenant.get("private_key_password"),
            "cas_portal_data_center": ext_tenant.get("cas_portal_data_center"),
            "cas_portal_url": ext_tenant.get("cas_portal_url"),
            "cloudappsecuritytoken": ext_tenant.get("cloudappsecuritytoken"),
        }

        return tenant

    def _load_endpoint(self, endpoint):
        conf_name = "splunk_ta_o365_endpoints"
        conf_content = self._get_conf_content(conf_name, endpoint)

        return (
            conf_content.get("Login"),
            conf_content.get("MessageTraceLogin"),
            conf_content.get("Management"),
            conf_content.get("Graph"),
            conf_content.get("CloudAppSecurity"),
            conf_content.get("MessageTrace"),
        )

    def _validate_credentials_v2_cert_based(
        self,
        session,
        login,
        resource,
        tenant_id,
        client_id,
        cert_private_key,
        cert_thumbprint,
        private_key_password,
    ):
        """
        Validates the user provided credentials for the certificate based authentication.
        Args:
            session (Requests): requests session object.
            login (str): Login endpoint.
            resource (str): Resource used in the scope for the request to API.
            tenant_id (str): Tenant ID provided by user.
            client_id (str): Client ID provided by user.
            cert_private_key (str): Private Key of the Certificate.
            cert_thumbprint (str): Thumbprint of the certificate from azure.
            private_key_password (str): Password of Private Key if it is encrypted.

        Raises:
            Exception: If UnicodeEncodeError occurs while ingesting the event, sanitise the data by using "backslashreplace" and then send event for ingestion.
        """
        scope = resource + "/.default"
        if not cert_private_key or not cert_thumbprint:
            raise Exception(
                "Certificate Credentials are not provided. Please enter the credentials."
            )
        cert_based_auth = O365LoginPortal(tenant_id, login.encode())
        response = cert_based_auth.get_cert_based_access_token(
            client_id,
            scope,
            session,
            cert_private_key,
            cert_thumbprint,
            private_key_password,
        )

        if response.status_code != 200:
            default_msg = (
                f"Unknown server response with status code {response.status_code}."
                " Please re-check provided certificate credentials."
            )
            trace = response.json()
            msg = trace.get("error_description", default_msg)
            return False, self._error(400, msg, trace)
        return True, self._response(200)

    def _validate_credentials_v2(
        self, session, login, resource, tenant_id, client_id, client_secret
    ):
        login = self._convert(login)
        tenant_id = self._convert(tenant_id)

        scope = resource + "/.default"

        url = urllib.parse.urljoin(login, f"/{tenant_id}/oauth2/v2.0/token")
        response = session.request(
            "POST",
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": scope,
            },
        )

        if response.status_code != 200:
            default_msg = (
                f"Unknown server response with status code {response.status_code}."
                " Please re-check provided client credentials."
            )
            trace = response.json()
            msg = trace.get("error_description", default_msg)
            return False, self._error(400, msg, trace)
        return True, self._response(200)

    def _validate_cas_token(
        self,
        session,
        cloudappsecurity,
        cloudappsecuritytoken,
        casPortalUrl,
        casPortalDataCenter,
    ):
        cloudappsecuritytoken = self._convert(cloudappsecuritytoken)
        cas_subdomain = (
            self._convert(casPortalUrl) + "." + self._convert(casPortalDataCenter)
        )
        cloudappsecurity = self._convert(cloudappsecurity)
        cloudappsecurity = cloudappsecurity.replace(
            "tenant_subdomain.tenant_data_center", cas_subdomain
        )

        url = urllib.parse.urljoin(cloudappsecurity, "/api/v1/{}/".format("alerts"))

        try:
            response = session.request(
                "GET",
                url,
                headers={
                    "Authorization": f"Token {cloudappsecuritytoken}",
                    "Content-Type": "application/json",
                },
            )
        except Exception as exc:  # noqa: F841
            return False, self._error(400, "Invalid Tenant Data Center.")

        if response.status_code != 200:
            trace = response.json()
            default_msg = (
                f"Unknown server response with status code {response.status_code}."
                " Please re-check provided Cloud App Security credentials."
            )
            msg = trace.get("error_description", trace.get("detail", default_msg))
            if msg != default_msg:
                msg = f"Please re-check provided Cloud App Security credentials. Error: {msg}"
            return False, self._error(400, msg, trace)
        return True, self._response(200)

    def validate(self):
        try:
            tenant = (
                self._load_existing_tenant(self._tenant_name)
                if not self._is_create
                else dict()
            )

            tenant_id = self._updated_tenant.get("tenant_id")
            client_id = self._updated_tenant.get("client_id")
            client_secret = (
                tenant.get("client_secret")
                if not self._is_create
                and self._updated_tenant["change_client_secret"] == "0"
                else self._updated_tenant.get("client_secret")
            )
            cert_private_key = (
                tenant.get("cert_private_key")
                if not self._is_create
                and self._updated_tenant["change_cert_creds"] == "0"
                else self._updated_tenant.get("cert_private_key")
            )
            private_key_password = (
                tenant.get("private_key_password")
                if not self._is_create
                and self._updated_tenant["change_cert_creds"] == "0"
                else self._updated_tenant.get("private_key_password")
            )
            cert_thumbprint = self._updated_tenant.get("cert_thumbprint")
            auth_type = self._updated_tenant.get("auth_type")
            cloudappsecuritytoken = (
                tenant.get("cloudappsecuritytoken")
                if not self._is_create
                and self._updated_tenant["change_cas_secret"] == "0"
                else self._updated_tenant.get("cloudappsecuritytoken")
            )
            casPortalUrl = self._updated_tenant.get("cas_portal_url")
            casPortalDataCenter = self._updated_tenant.get("cas_portal_data_center")
            endpoint = self._updated_tenant.get("endpoint")

            (
                login,
                msg_trace_login_gcc,
                mgmt,
                graph,
                cloudappsecurity,
                messagetrace,
            ) = self._load_endpoint(endpoint)
            config = get_config_manager(self._session_key)
            proxy = Proxy.load(config)
            session = proxy.create_requests_session()

            if tenant_id:
                if login and (mgmt or graph or messagetrace):
                    is_valid_mgmt = is_valid_graph = is_valid_messagetrace = False

                    if mgmt:
                        logger.info(f"Validating Management API, {mgmt}")
                        if auth_type == "cert_based":
                            (
                                is_valid_mgmt,
                                mgmt_res,
                            ) = self._validate_credentials_v2_cert_based(
                                session,
                                login,
                                mgmt,
                                tenant_id,
                                client_id,
                                cert_private_key,
                                cert_thumbprint,
                                private_key_password,
                            )
                        else:
                            is_valid_mgmt, mgmt_res = self._validate_credentials_v2(
                                session,
                                login,
                                mgmt,
                                tenant_id,
                                client_id,
                                client_secret,
                            )
                        if not is_valid_mgmt:
                            logger.error(
                                f"Validation failed for the Management API. Reason: {mgmt_res}"
                            )
                    if graph:
                        logger.info(f"Validating Graph API, {graph}")
                        if auth_type == "cert_based":
                            (
                                is_valid_graph,
                                graph_res,
                            ) = self._validate_credentials_v2_cert_based(
                                session,
                                login,
                                graph,
                                tenant_id,
                                client_id,
                                cert_private_key,
                                cert_thumbprint,
                                private_key_password,
                            )
                        else:
                            is_valid_graph, graph_res = self._validate_credentials_v2(
                                session,
                                login,
                                graph,
                                tenant_id,
                                client_id,
                                client_secret,
                            )
                        if not is_valid_graph:
                            logger.error(
                                f"Validation failed for the Graph API. Reason: {graph_res}"
                            )
                    if messagetrace:
                        login_for_messagetrace = (
                            msg_trace_login_gcc
                            if endpoint == "USGovGCC" and msg_trace_login_gcc
                            else login
                        )
                        if auth_type == "cert_based":
                            (
                                is_valid_messagetrace,
                                messagetrace_res,
                            ) = self._validate_credentials_v2_cert_based(
                                session,
                                login_for_messagetrace,
                                messagetrace,
                                tenant_id,
                                client_id,
                                cert_private_key,
                                cert_thumbprint,
                                private_key_password,
                            )
                        else:
                            (
                                is_valid_messagetrace,
                                messagetrace_res,
                            ) = self._validate_credentials_v2(
                                session,
                                login_for_messagetrace,
                                messagetrace,
                                tenant_id,
                                client_id,
                                client_secret,
                            )
                        if not is_valid_messagetrace:
                            logger.error(
                                f"Validation failed for the Message Trace API. Reason: {messagetrace_res}"
                            )

                    if not (is_valid_mgmt or is_valid_graph or is_valid_messagetrace):
                        if not is_valid_mgmt:
                            return mgmt_res
                        if not is_valid_graph:
                            return graph_res
                        if not is_valid_messagetrace:
                            return messagetrace_res
                else:
                    logger.error(
                        "Graph/Management/MessageTrace APIs for the selected 'Endpoint' not found."
                    )
                    return self._error(
                        400,
                        "Graph/Management/MessageTrace APIs for the selected 'Endpoint' not found.",
                    )

            if cloudappsecuritytoken:
                if cloudappsecurity:
                    is_valid, cloud_res = self._validate_cas_token(
                        session,
                        cloudappsecurity,
                        cloudappsecuritytoken,
                        casPortalUrl,
                        casPortalDataCenter,
                    )
                    if not is_valid:
                        logger.error(
                            f"Validation failed for the Cloud App Security APIs. Reason: {cloud_res}"
                        )
                        return cloud_res
                else:
                    logger.error(
                        "Cloud App Security APIs for the selected 'Endpoint' not found."
                    )
                    return self._error(
                        400,
                        "Cloud App Security APIs for the selected 'Endpoint' not found.",
                    )
            logger.info("Tenant validated successfully.")
            return self._response(200)
        except Exception as e:
            logger.error(
                f"Error occurred while validating the tenant. Error: {str(e)}",
                exc_info=True,
            )
            return self._error(500, str(e))


class TenantHandler(AdminExternalHandler):
    """
    Custom handler to handle Tenant operations
    """

    def _remove_change_secret_params(self):
        # remove change secret parameters which are required for UI behaviour
        # and not in data collection
        if "change_client_secret" in self.payload:
            del self.payload["change_client_secret"]
        if "change_cert_creds" in self.payload:
            del self.payload["change_cert_creds"]
        if "change_cas_secret" in self.payload:
            del self.payload["change_cas_secret"]

    def _validate(self, name, updated_tenant, is_create=False):
        tenant_validator = TenantValidator(
            self.getSessionKey(), name, updated_tenant, is_create
        )
        result = tenant_validator.validate()
        if result.get("status") < 200 or result.get("status") >= 300:
            message = result.get("payload")
            try:
                payload_dict = json.loads(message)
                messages = payload_dict.get("messages")
                if messages:
                    message = messages[0].get("text")
            except Exception as e:
                msg = f"Error={e}, Error Detail={result}"
                logger.error(msg)
                return "Unexpected error", msg
            return result.get("status"), message
        return None, None

    def _handle_fields_based_on_auth_type(self):
        if self.payload["auth_type"] == "secret_based":
            self.payload["cert_private_key"] = ""
            self.payload["cert_thumbprint"] = ""
            self.payload["private_key_password"] = ""
        elif self.payload["auth_type"] == "cert_based":
            self.payload["client_secret"] = ""

    def _validate_certificate_thumbprint(self):
        validator = CertThumbprintValidator()
        result, message = validator.validate(self.payload)
        if not result:
            raise RestError(400, message)

    def handleCreate(self, confInfo):
        name = self.callerArgs.id
        updated_tenant = self.payload.copy()
        self._validate_certificate_thumbprint()
        status, message = self._validate(name, updated_tenant, is_create=True)
        if status:
            raise RestError(status, message)
        self._handle_fields_based_on_auth_type()
        self._remove_change_secret_params()
        self.payload["is_conf_migrated"] = 1
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        updated_tenant = self.payload.copy()
        self._validate_certificate_thumbprint()
        status, message = self._validate(name, updated_tenant, is_create=False)
        if status:
            raise RestError(status, message)
        if self.payload["change_client_secret"] == "0":
            del self.payload["client_secret"]
        if self.payload["change_cert_creds"] == "0":
            del self.payload["cert_private_key"]
            del self.payload["private_key_password"]
        if self.payload["change_cas_secret"] == "0":
            del self.payload["cloudappsecuritytoken"]
        self._handle_fields_based_on_auth_type()
        self._remove_change_secret_params()
        self.payload["is_conf_migrated"] = 1
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=TenantHandler,
    )
