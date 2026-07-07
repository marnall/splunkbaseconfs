#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test
import logging

from typing import Any, Dict
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        "name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[0-9|a-z|A-Z][\w\-]*$""",
        ),
    )
]

fields = [
    field.RestField(
        "manager", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "per_file_exec", required=True, encrypted=False, default=1, validator=None
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=3,
        validator=validator.Number(
            max_val=300,
            min_val=1,
        ),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = DataInputModel(
    "managed_consumer_input",
    model,
)


class ManagedConsumerConfigHandler(AdminExternalHandler):
    def validate_interval(self) -> None:
        if "disabled" in self.callerArgs.data:
            return

        try:
            interval = int(self.callerArgs.data.get("interval", [""])[0])
        except ValueError as ve:
            raise RestError(
                409,
                "Interval is not an integer value. Please follow field help notes to specify correct value.",
            )

        per_file_exec = self.callerArgs.data.get("per_file_exec", ["0"])[0]

        if per_file_exec == "1" and (interval < 1 or interval > 10):
            raise RestError(
                409,
                "For per data file modinput execution mode interval value must be in range [1, 10] seconds. Recommended interval is 3 seconds.",
            )

    def handleCreate(self, confInfo: Dict[str, Any]) -> None:
        self.validate_interval()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo: Dict[str, Any]) -> None:
        self.validate_interval()
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=ManagedConsumerConfigHandler,
    )
