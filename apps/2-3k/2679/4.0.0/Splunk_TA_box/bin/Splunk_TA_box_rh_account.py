#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging
import json
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
        default="account.box.com",
        validator=None,
    ),
    field.RestField(
        "client_id", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "client_secret", required=False, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "redirect_url", required=False, encrypted=False, default=None, validator=None
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
        "box_subject_id", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "access_token", required=False, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "refresh_token", required=False, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "instance_url", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "auth_type", required=False, encrypted=False, default=None, validator=None
    ),
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    "splunk_ta_box_account",
    model,
    config_name="account",
    need_reload=False,
)

APP_NAME = "Splunk_TA_box"
OAUTH_ENDPOINT = "Splunk_TA_box_oauth"
TOKEN_ENDPOINT = "/api/oauth2/token"


class HandlerWithOauth(AdminExternalHandler):
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

        return f"https://{host}/{TOKEN_ENDPOINT.lstrip('/')}"

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

        box_subject_id = self.callerArgs.data.get("box_subject_id", [None])[0]

        params = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "box_subject_id": box_subject_id,
            "box_subject_type": "user",
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

    def handleCreate(self, confInfo):
        self.oauth_client_credentials_call()
        return super().handleCreate(confInfo)

    def handleEdit(self, confInfo):
        self.oauth_client_credentials_call()
        return super().handleEdit(confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=HandlerWithOauth,
    )
