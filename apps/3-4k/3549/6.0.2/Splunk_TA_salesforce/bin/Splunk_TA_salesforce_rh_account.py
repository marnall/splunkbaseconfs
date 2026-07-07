#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This file contains certain ignores for certain linters.

* isort ignores:
- isort: skip = Particular import must be the first import or it is conflicting with the black linter formatting.

* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""
from typing import Dict, Any

import import_declare_test  # isort: skip # noqa: F401

import logging
import json

from Splunk_TA_salesforce_rh_account_validation import AccountValidation
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    RestModel,
    SingleModel,
    field,
    validator,
)
from solnlib import splunk_rest_client as rest_client
from splunk.admin import InternalException

util.remove_http_proxy_env_vars()

special_fields = [
    field.RestField(
        "name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=50,
                min_len=1,
            ),
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""",
            ),
        ),
    )
]

fields = [
    field.RestField(
        "endpoint",
        required=False,
        encrypted=False,
        default="login.salesforce.com",
        validator=validator.Pattern(
            regex="^(?!https?:).*",
        ),
    ),
    field.RestField(
        "username",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(min_len=1, max_len=256),
    ),
    field.RestField(
        "password",
        required=False,
        encrypted=True,
        default=None,
        validator=validator.AllOf(
            validator.String(min_len=1, max_len=16000), AccountValidation()
        ),
    ),
    field.RestField(
        "token",
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(min_len=1, max_len=8192),
    ),
    field.RestField(
        "client_id",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(min_len=1, max_len=8192),
    ),
    field.RestField(
        "client_secret",
        required=False,
        encrypted=True,
        default=None,
        validator=validator.AllOf(
            validator.String(min_len=1, max_len=8192), AccountValidation()
        ),
    ),
    field.RestField(
        "redirect_url", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "access_token",
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(min_len=1, max_len=8192),
    ),
    field.RestField(
        "client_id_oauth_credentials",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "client_secret_oauth_credentials",
        required=False,
        encrypted=True,
        default=None,
        validator=None,
    ),
    field.RestField(
        "refresh_token",
        required=False,
        encrypted=True,
        default=None,
        validator=None,
    ),
    field.RestField(
        "instance_url", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "auth_type",
        required=True,
        encrypted=False,
        default="basic",
        validator=validator.Enum(
            ("basic", "oauth", "oauth_client_credentials"),
        ),
    ),
    field.RestField(
        "sfdc_api_version",
        required=True,
        encrypted=False,
        default="64.0",
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^\d{2}\.\d$""",
            ),
            validator.Number(42.0, 64.0),
        ),
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("splunk_ta_salesforce_account", model, config_name="account")


APP_NAME = "Splunk_TA_salesforce"
OAUTH_ENDPOINT = "Splunk_TA_salesforce_oauth"
TOKEN_ENDPOINT = "/services/oauth2/token"


class SalesforceAccountHandler(AdminExternalHandler):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._oauth_url = f"/servicesNS/nobody/{APP_NAME}/{OAUTH_ENDPOINT}/oauth"
        self._rest_client = rest_client.SplunkRestClient(
            self.getSessionKey(),
            app=APP_NAME,
        )

    def oauth_call_url(self):
        host = (
            self.callerArgs.data.get("endpoint_token_oauth_credentials", [None])[0]
            or self.callerArgs.data.get("endpoint_token", [None])[0]
            or self.callerArgs.data.get("endpoint", [None])[0]
        )
        if host:
            return f"https://{host}/{TOKEN_ENDPOINT.lstrip('/')}"
        else:
            host = self.callerArgs.data.get("url", [None])[0]
            host = host.rstrip("/")
            return f"{host}/{TOKEN_ENDPOINT.lstrip('/')}"

    def oauth_client_credentials_call(self):
        auth_type = self.callerArgs.data.get("auth_type", [""])[0]
        if auth_type != "oauth_client_credentials":
            return

        client_id = (
            self.callerArgs.data.get("client_id_oauth_credentials", [None])[0]
            or self.callerArgs.data.get("client_id", [None])[0]
        )

        client_secret = (
            self.callerArgs.data.get("client_secret_oauth_credentials", [None])[0]
            or self.callerArgs.data.get("client_secret", [None])[0]
        )

        params = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "url": self.oauth_call_url(),
            "method": "POST",
        }

        if "scope" in self.callerArgs.data:
            params["scope"] = self.callerArgs.data.get("scope", [None])[0]

        data = json.loads(
            self._rest_client.post(
                self._oauth_url,
                body=params,
                headers=[("Content-Type", "application/json")],
                output_mode="json",
            )
            .body.read()
            .decode("utf-8")
        )["entry"][0]["content"]

        if "access_token" not in data:
            data = data.get("error", data)
            raise InternalException(
                "Error while trying to obtain OAuth token: %s" % data
            )
        self.payload["access_token"] = data["access_token"]

        for key in ["refresh_token", "instance_url"]:
            if key in data:
                self.payload[key] = data[key]

    def handleCreate(self, confInfo: Dict[str, Any]) -> None:
        self.oauth_client_credentials_call()
        return super().handleCreate(confInfo)

    def handleEdit(self, confInfo: Dict[str, Any]) -> None:
        AdminExternalHandler.handleRemove(self, confInfo)
        self.oauth_client_credentials_call()
        AdminExternalHandler.handleCreate(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=SalesforceAccountHandler,
    )
