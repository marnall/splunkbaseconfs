#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""

* isort ignores:
- isort: skip = Should not be sorted.
* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import splunk_ta_remedy_declare  # isort: skip # noqa: F401

import logging

from splunk_ta_remedy_rest_account_validation import RestAccountValidation
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
        "midtier_url",
        required=True,
        encrypted=False,
        default="",
        validator=validator.Pattern(
            regex=r"""^(https://)[a-zA-Z0-9][a-zA-Z0-9\.\-]+:[0-9]+$""",
        ),
    ),
    field.RestField(
        "server_name",
        required=True,
        encrypted=False,
        default="",
        validator=validator.String(
            max_len=8192,
            min_len=0,
        ),
    ),
    field.RestField(
        "server_url",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(https://)[a-zA-Z0-9][a-zA-Z0-9\.\-]+:[0-9]+$""",
        ),
    ),
    field.RestField(
        "smart_it_url",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(https://)[a-zA-Z0-9][a-zA-Z0-9\.\-]+:[0-9]+$""",
        ),
    ),
    field.RestField(
        "username",
        required=True,
        encrypted=False,
        default=None,
        validator=RestAccountValidation(),
    ),
    field.RestField(
        "password", required=False, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "jwt_token", required=False, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "record_count",
        required=False,
        encrypted=False,
        default=2000,
        validator=validator.AllOf(
            validator.Number(
                max_val=10000,
                min_val=1000,
            ),
            validator.Pattern(
                regex=r"""^\d+$""",
            ),
        ),
    ),
    field.RestField(
        "disable_ssl_certificate_validation",
        required=False,
        encrypted=False,
        default=0,
        validator=None,
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("splunk_ta_remedy_account", model, config_name="account")


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
