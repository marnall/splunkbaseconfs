#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import logging

import import_declare_test  # noqa: F401

from crowdstrike_fdr_ta_lib import aws_helpers, config_builders
from crowdstrike_fdr_ta_lib.constants import APP_NAME
from crowdstrike_fdr_ta_lib.splunk_helpers import CSScriptHelper
from crowdstrike_fdr_ta_lib.logger_adapter import ModinputLoggerProxy

from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    RestModel,
    SingleModel,
    field,
    validator,
)
from splunktaucclib.rest_handler.error import RestError
from typing import Dict, Any

logger = ModinputLoggerProxy("aws_session_rh")

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        "aws_region", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "aws_access_key_id",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
    field.RestField(
        "aws_secret_access_key",
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    "splunk_ta_crowdstrike_fdr_aws_collections", model, config_name="aws_collections"
)


class ValidateAWSCredsExternalHandler(AdminExternalHandler):
    def validate_aws_session_info(self) -> None:
        try:
            info = dict(
                region_name=self.callerArgs.data["aws_region"][0],
                aws_access_key_id=self.callerArgs.data["aws_access_key_id"][0],
                aws_secret_access_key=self.callerArgs.data["aws_secret_access_key"][0],
            )

            ta_settings = CSScriptHelper.load_config(
                None,
                APP_NAME,
                "splunk_ta_crowdstrike_fdr_settings",
                "TA settings",
                self.getSessionKey(),
            )
            aws_proxy_config = config_builders.build_aws_proxy_config(ta_settings)
            info.update(aws_proxy_config)

            if not aws_helpers.aws_validate_credentials(info):
                raise RestError(
                    409,
                    "Failed to connect/authenticate to AWS environment. "
                    "Invalid FDR AWS collection information provided or if connection requires proxy, "
                    "please make sure that Configuration => Proxy settings are correct",
                )
        except Exception as e:
            raise RestError(400, str(e)) from e

    def handleCreate(self, confInfo: Dict[str, Any]) -> None:
        self.validate_aws_session_info()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo: Dict[str, Any]) -> None:
        self.validate_aws_session_info()
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=ValidateAWSCredsExternalHandler,
    )
