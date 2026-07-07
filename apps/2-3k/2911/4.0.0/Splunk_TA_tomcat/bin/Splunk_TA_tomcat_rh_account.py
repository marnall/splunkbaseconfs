#
# SPDX-FileCopyrightText: 2026 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import logging

import import_declare_test
from Splunk_TA_tomcat_account_validator import ServerValidator
from splunktaucclib.rest_handler import admin_external
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    RestModel,
    SingleModel,
    field,
    validator,
)

assert import_declare_test, "Module is used to filter the sys.path"

fields = [
    field.RestField(
        "jmx_url",
        required=True,
        encrypted=False,
        default="",
        validator=validator.Pattern(
            regex=r"""^service:jmx.*$""",
        ),
    ),
    field.RestField(
        "username",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255,
            min_len=1,
        ),
    ),
    field.RestField(
        "password",
        required=True,
        encrypted=True,
        default=None,
        validator=ServerValidator(),
    ),
]

model = RestModel(fields, name=None)


endpoint = SingleModel("splunk_ta_tomcat_account", model, config_name="account")


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
