#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test

import logging

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

from crowdstrike_fdr_ta_lib.crowdstrike_helpers import (
    CrowdStrikeClient,
    CrowdStrikeApiAuthorizationFailed,
)
from crowdstrike_fdr_ta_lib.constants import APP_NAME
from crowdstrike_fdr_ta_lib.splunk_helpers import CSScriptHelper
from crowdstrike_fdr_ta_lib.config_builders import build_proxy_connecton_string
from typing import Dict, Any

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        "api_client_id",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
    field.RestField(
        "api_client_secret",
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
    field.RestField(
        "api_base_url",
        required=True,
        encrypted=False,
        default="https://api.crowdstrike.com",
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=600,
        validator=validator.Number(
            max_val=86400,
            min_val=60,
        ),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "device_api_inventory_sync_service",
    model,
)


class DeviceApiInvSyncExternalHandler(AdminExternalHandler):
    def validate_api_gteway_connection_info(self) -> None:
        if "disabled" in self.callerArgs.data:
            return

        err = (
            "CrowdStrike API gateway connection information validation failed. "
            + "Make sure that corect connection information is provided or if connection requires proxy, "
            + "please make sure that Configuration => Proxy settings are correct"
        )

        try:
            ta_settings = CSScriptHelper.load_config(
                None,
                APP_NAME,
                "splunk_ta_crowdstrike_fdr_settings",
                "TA settings",
                self.getSessionKey(),
            )

            config_proxy = ta_settings.get("proxy")

            cs_connect = dict(
                base_url=self.callerArgs.data["api_base_url"][0],
                client_id=self.callerArgs.data["api_client_id"][0],
                client_secret=self.callerArgs.data["api_client_secret"][0],
                proxy=build_proxy_connecton_string(config_proxy),
            )

            client = CrowdStrikeClient(**cs_connect)
            if not client.auth(force=True):
                raise Exception("Authentication failed, no token has been returned")

        except CrowdStrikeApiAuthorizationFailed:
            raise RestError(409, err)
        except Exception as e:
            raise RestError(409, err) from e

    def handleCreate(self, confInfo: Dict[str, Any]) -> None:
        self.validate_api_gteway_connection_info()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo: Dict[str, Any]) -> None:
        self.validate_api_gteway_connection_info()
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=DeviceApiInvSyncExternalHandler,
    )
