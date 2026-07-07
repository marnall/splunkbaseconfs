#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
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
from splunktaucclib.rest_handler.error import RestError
from splunk_ta_cisco_ucs_utility import do_input_exists
from splunk_ta_cisco_ucs_server_validation import AccountValidation
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "description",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255,
            min_len=0,
        ),
    ),
    field.RestField(
        "server_url",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9:][a-zA-Z0-9\.\-:]+$""",
            ),
            validator.String(
                max_len=4096,
                min_len=0,
            ),
        ),
    ),
    field.RestField(
        "account_name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255,
            min_len=1,
        ),
    ),
    field.RestField(
        "account_password",
        required=True,
        encrypted=True,
        default=None,
        validator=AccountValidation(),
    ),
    field.RestField(
        "disable_ssl_verification",
        required=False,
        encrypted=False,
        default=0,
        validator=None,
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("splunk_ta_cisco_ucs_servers", model, config_name="servers")


class CiscoUCSServerHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, confInfo):
        # Check if input is using the server that user requested to delete
        exists_flag, input_name = do_input_exists(
            "servers", self.callerArgs.id, self.getSessionKey()
        )
        if exists_flag:
            raise RestError(
                409,
                "Cannot delete the manager as it is configured in the input - {}".format(
                    input_name
                ),
            )
        AdminExternalHandler.handleRemove(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CiscoUCSServerHandler,
    )
