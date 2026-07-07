#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # noqa # isort: skip
import json
import logging

import splunk.rest as rest
from splunk.admin import InternalException
from solnlib import conf_manager, log
from Splunk_TA_okta_identity_cloud_account_validation import AccountValidation
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from solnlib import splunk_rest_client as rest_client
from splunktaucclib.rest_handler.endpoint import (
    RestModel,
    SingleModel,
    field,
    validator,
)
from splunktaucclib.rest_handler.error import RestError
from constant import APP_NAME, OAUTH_ENDPOINT, TOKEN_ENDPOINT, DEFAULT_SCOPE

util.remove_http_proxy_env_vars()


"""
Every configuration object must have a unique and valid name that matches this format.
- Name of stanza in the conf file
"""
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
        "domain",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=1024,
            min_len=8,
        ),
    ),
    field.RestField(
        "password",
        required=False,
        encrypted=True,
        default=None,
        validator=AccountValidation(),
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
        "endpoint", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "endpoint_url", required=False, encrypted=False, default=None, validator=None
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
        "scope", required=False, encrypted=False, default=None, validator=None
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
        "auth_type", required=True, encrypted=False, default="basic", validator=None
    ),
]
model = RestModel(fields, name=None, special_fields=special_fields)

endpoint = SingleModel(
    "splunk_ta_okta_identity_cloud_account",
    model,
    config_name="account",
    need_reload=False,
)


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
            or self.callerArgs.data.get("endpoint_url", [None])[0]
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

    def handleCreate(self, confInfo):
        self.oauth_client_credentials_call()
        self.payload["scope"] = DEFAULT_SCOPE
        return super().handleCreate(confInfo)

    def handleEdit(self, confInfo):
        self.oauth_client_credentials_call()
        self.payload["scope"] = DEFAULT_SCOPE
        return super().handleEdit(confInfo)

    def handleRemove(self, confInfo):
        session_key = self.getSessionKey()
        server_name = self.callerArgs.id
        logger = log.Logs().get_logger(
            "splunk_ta_okta_identity_cloud_account_validation"
        )
        log_level = conf_manager.get_log_level(
            logger=logger,
            session_key=session_key,
            app_name=APP_NAME,
            conf_name="splunk_ta_okta_identity_cloud_settings",
        )
        logger.setLevel(log_level)
        input_list = []
        input_list_str = None
        DELETE_ERROR_MSG = (
            "Cannot delete the account as it is already being used in {}."
        )
        try:
            response_status, response_content = rest.simpleRequest(
                "/servicesNS/nobody/" + str(APP_NAME) + "/configs/conf-inputs/",
                sessionKey=session_key,
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )
            res = json.loads(response_content)

            if "entry" in res:
                for inputs in res["entry"]:
                    if "name" in inputs:
                        input_name = inputs["name"]
                        if (
                            "app" in inputs.get("acl", "")
                            and inputs["acl"].get("app", "") == APP_NAME
                        ):
                            if (
                                "content" in inputs
                                and "global_account" in inputs["content"]
                            ):
                                account_name = inputs["content"]["global_account"]
                                if account_name == server_name:
                                    input_list.append(input_name.split("//")[1])

                if len(input_list) > 0:
                    if len(input_list) > 2:
                        input_list_str = (
                            ", ".join(input_list[:-1]) + ", and " + str(input_list[-1])
                        )
                    elif len(input_list) == 2:
                        input_list_str = " and ".join(input_list)
                    else:
                        input_list_str = input_list[0]

                    raise RestError(
                        409,
                        DELETE_ERROR_MSG.format(input_list_str),
                    )
        except Exception:
            logger.error(DELETE_ERROR_MSG.format(input_list_str))
            raise RestError(
                409,
                DELETE_ERROR_MSG.format(input_list_str),
            )
        AdminExternalHandler.handleRemove(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=HandlerWithOauth,
    )
