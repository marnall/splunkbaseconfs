#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import logging

from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

from splunktaucclib.rest_handler.endpoint import (  # isort: skip
    DataInputModel,
    RestModel,
    field,
    validator,
)

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "description", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "servers", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "templates", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "duration",
        required=True,
        encrypted=False,
        default="3600",
        validator=validator.Number(min_val=1, max_val=31536000, is_int=True),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.String(
            max_len=80,
            min_len=1,
        ),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "citrix_netscaler",
    model,
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
