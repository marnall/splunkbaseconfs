#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import logging

from solnlib import conf_manager
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
from ta_util2 import utils

from splunktaucclib.rest_handler.endpoint import (  # isort:skip # noqa: F401
    field,
    validator,
    RestModel,
    SingleModel,
)

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "description", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "metrics", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "helpLink", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "content", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("citrix_netscaler_templates", model, config_name="template")


class CitrixTemplateExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    # Override the delete template method to prevent deletion of template which is in use
    def handleRemove(self, confInfo):
        # Get the name of the app
        app_name = utils.get_appname_from_path(__file__)
        # Get the name of the template from the callerArgs
        template_name = self.callerArgs.id
        # Create confmanager object for the Citrix Netscaler addon
        cfm = conf_manager.ConfManager(self.getSessionKey(), app_name)
        # Get all the inputs stanzas from the addon
        input_objs_dict = cfm.get_conf("inputs").get_all(only_current_app=True)
        # Iterate through all the input stanzas
        for input, input_info in list(input_objs_dict.items()):
            # Skip the default input stanza
            if input != "citrix_netscaler":
                templates = input_info.get("templates") or ""
                # If the use of the given template found in inputs then raise the error
                if template_name in templates.split("|"):
                    raise RestError(
                        405,
                        '"{}" cannot be deleted because it is in use.'.format(
                            template_name
                        ),
                    )
        # If template is not in use, continue to remove the template by calling super method
        AdminExternalHandler.handleRemove(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CitrixTemplateExternalHandler,
    )
