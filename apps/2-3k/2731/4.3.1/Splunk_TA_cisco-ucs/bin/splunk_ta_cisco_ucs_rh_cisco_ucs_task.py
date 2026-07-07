#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
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
        "interval",
        required=True,
        encrypted=False,
        default=300,
        validator=validator.Number(max_val=31536000, min_val=1, is_int=True),
    ),
    field.RestField(
        "sourcetype",
        required=True,
        encrypted=False,
        default="cisco:ucs",
        validator=validator.String(
            max_len=1024,
            min_len=1,
        ),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.AllOf(
            validator.String(
                max_len=1023,
                min_len=1,
            ),
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9][a-zA-Z0-9\_\-]*$""",
            ),
        ),
    ),
    field.RestField(
        "servers", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "templates", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "cisco_ucs_task",
    model,
)

if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
