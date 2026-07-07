#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
Rest handler file for the scom settings.

* isort ignores:
- isort: skip = Should not be sorted.

* flake8 ignores:
- noqa: E401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path

"""


import import_declare_test  # isort: skip # noqa: F401
import logging
import re

import splunk_ta_ms_scom_util as scom_util
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

from splunktaucclib.rest_handler.endpoint import (  # isort: skip
    MultipleModel,
    RestModel,
    field,
    validator,
)


util.remove_http_proxy_env_vars()


fields_logging = [
    field.RestField(
        "log_level",
        required=True,
        encrypted=False,
        default="WARN",
        validator=validator.Enum(("DEBUG", "WARN", "ERROR")),
    )
]
model_logging = RestModel(fields_logging, name="logging")


endpoint = MultipleModel(
    "microsoft_scom",
    models=[model_logging],
)


class ScomSettingHandler(AdminExternalHandler):
    """
    Manage SCOM Setting Details.
    """

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def _update_loglevel(self, log_level):
        all_inputs = scom_util.get_all_internal_inputs(
            self.getSessionKey(), self.userName, self.appName
        )
        for name, script in list(all_inputs.items()):
            if "-loglevel" in script:
                script = re.sub(
                    r"-loglevel\s*\S+\s*", r"-loglevel {} ".format(log_level), script
                )
            else:
                script = "{} -loglevel {}".format(script, log_level)

            data = {"script": script}
            success = scom_util.update_internal_inputs(
                name, data, self.getSessionKey(), self.userName, self.appName
            )
            if not success:
                msgx = "cannot update loglevel attribute in inputs.conf"
                raise RestError("400", str(msgx))

    def handleEdit(self, confInfo):
        if self.callerArgs.id == "logging":
            log_level = self.callerArgs.data.get("log_level")[0]
            self._update_loglevel(log_level)

        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=ScomSettingHandler,
    )
