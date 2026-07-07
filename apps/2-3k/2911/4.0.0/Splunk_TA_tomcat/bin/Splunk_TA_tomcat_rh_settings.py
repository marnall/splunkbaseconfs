#
# SPDX-FileCopyrightText: 2026 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import logging

import import_declare_test
from splunktaucclib.rest_handler import admin_external
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import MultipleModel, RestModel, field

assert import_declare_test, "Module is used to filter the sys.path"

fields_logging = [
    field.RestField(
        "loglevel",
        required=True,
        encrypted=False,
        default="INFO",
        validator=None,
    )
]
model_logging = RestModel(fields_logging, name="logging")


endpoint = MultipleModel(
    "splunk_ta_tomcat_settings",
    models=[model_logging],
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
