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
        "content", required=True, encrypted=False, default=None, validator=None
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("splunk_ta_cisco_ucs_templates", model, config_name="templates")


class CiscoUCSTemplateHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, confInfo):
        default_templates = ["UCS_Inventory", "UCS_Performance", "UCS_Fault"]

        # Check if the template user wants to delete is one of the pre-defined/default templates
        if self.callerArgs.id in default_templates:
            raise RestError(
                409,
                '"{}" cannot be deleted because it is default template.'.format(
                    self.callerArgs.id
                ),
            )

        # Check if input is using the template user wants to delete
        exists_flag, input_name = do_input_exists(
            "templates", self.callerArgs.id, self.getSessionKey()
        )
        if exists_flag:
            raise RestError(
                409,
                "Cannot delete the template as it is configured in the input - {}".format(
                    input_name
                ),
            )
        AdminExternalHandler.handleRemove(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CiscoUCSTemplateHandler,
    )
