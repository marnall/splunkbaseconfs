#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import logging

import import_declare_test  # noqa: F401
from crowdstrike_fdr_ta_lib import splunk_helpers
from crowdstrike_fdr_ta_lib.constants import APP_NAME
from crowdstrike_fdr_ta_lib.logger_adapter import ModinputLoggerProxy
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator,
)
from splunktaucclib.rest_handler.error import RestError
from typing import Dict, Any

logger = ModinputLoggerProxy("inventory_sync_service_rh")


util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        "search_head_address",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
    field.RestField(
        "search_head_port",
        required=True,
        encrypted=False,
        default="8089",
        validator=validator.Number(
            max_val=65535,
            min_val=1,
        ),
    ),
    field.RestField(
        "search_head_username",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
    field.RestField(
        "search_head_password",
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
    field.RestField(
        "use_failover_search_head",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "failover_search_head_address",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
    field.RestField(
        "failover_search_head_port",
        required=False,
        encrypted=False,
        default="8089",
        validator=validator.Number(
            max_val=65535,
            min_val=1,
        ),
    ),
    field.RestField(
        "failover_search_head_username",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
    field.RestField(
        "failover_search_head_password",
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=200,
        validator=validator.Number(
            max_val=3600,
            min_val=30,
        ),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "inventory_sync_service",
    model,
)


class InventorySyncExternalHandler(AdminExternalHandler):
    def validate_sh_connection_info(self) -> None:
        if "disabled" in self.callerArgs.data:
            return

        for prefix in ["", "failover_"]:
            info = dict(
                host=self.callerArgs.data.get(f"{prefix}search_head_address", [None])[
                    0
                ],
                port=self.callerArgs.data.get(f"{prefix}search_head_port", [None])[0],
                username=self.callerArgs.data.get(
                    f"{prefix}search_head_username", [None]
                )[0],
                password=self.callerArgs.data.get(
                    f"{prefix}search_head_password", [None]
                )[0],
                owner="nobody",
                app=APP_NAME,
            )

            try:
                success = splunk_helpers.validate_connection_info(info)
            except Exception as e:
                raise RestError(400, str(e))

            if not success:
                msg = (
                    "Invalid search head connection information provided, "
                    "failed to authenticate to {host}:{port}"
                )
                raise RestError(409, msg.format(**info))

            if self.callerArgs.data.get("use_failover_search_head", [None])[0] != "1":
                break

    def handleCreate(self, confInfo: Dict[str, Any]) -> None:
        self.validate_sh_connection_info()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo: Dict[str, Any]) -> None:
        self.validate_sh_connection_info()
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=InventorySyncExternalHandler,
    )
