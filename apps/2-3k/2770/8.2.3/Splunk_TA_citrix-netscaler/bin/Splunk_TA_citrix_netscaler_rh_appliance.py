#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import logging

from Splunk_TA_citrix_netscaler_account_validation import AccountValidation
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

from splunktaucclib.rest_handler.endpoint import (  # isort: skip
    RestModel,
    SingleModel,
    field,
    validator,
)

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "description", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "server_url",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^((?!://).)*$""",
        ),
    ),
    field.RestField(
        "account_name", required=True, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "account_password",
        required=True,
        encrypted=True,
        default=None,
        validator=AccountValidation(),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("citrix_netscaler_servers", model, config_name="appliance")


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
