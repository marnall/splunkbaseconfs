##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test  # noqa: F401 isort: skip

import logging

from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import MultipleModel  # noqa: F401

from splunktaucclib.rest_handler.endpoint import (  # noqa: F401 # isort:skip
    RestModel,
    field,
    validator,
)

util.remove_http_proxy_env_vars()


fields_logging = [
    field.RestField(
        "loglevel", required=False, encrypted=False, default="INFO", validator=None
    )
]
model_logging = RestModel(fields_logging, name="logging")


endpoint = MultipleModel(
    "splunk_ta_f5_settings",
    models=[model_logging],
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
