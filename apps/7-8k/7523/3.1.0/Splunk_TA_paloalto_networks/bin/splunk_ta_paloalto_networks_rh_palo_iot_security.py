#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import import_declare_test
import re

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(?:-1|\d+(?:\.\d+)?)$""",
        ),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.AllOf(
            validator.String(
                max_len=80,
                min_len=1,
            ),
            validator.Pattern(
                regex=r"""^[a-zA-Z][\w-]*$""",
            ),
        ),
    ),
    field.RestField(
        "iot_account",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z][\w-]*$""",
        ),
    ),
    field.RestField(
        "start_time",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$""",
        ),
    ),
    field.RestField(
        "disabled",
        required=False,
        validator=None,
    ),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "palo_iot_security",
    model,
)


class IoTSecurityHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self.input_name = self.callerArgs.id

    def _validate_name(self, name):
        pat = re.compile(r"^[a-zA-Z]\w*$")
        if not (re.fullmatch(pat, str(name)) and 1 < len(name) < 100):
            raise RestError(
                status="400",
                message="Input Name must start with a letter and followed by alphabetic letters, digits or underscores.",
            )

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        self._validate_name(self.input_name)
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        self._validate_name(self.input_name)
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        AdminExternalHandler.handleRemove(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=IoTSecurityHandler,
    )
