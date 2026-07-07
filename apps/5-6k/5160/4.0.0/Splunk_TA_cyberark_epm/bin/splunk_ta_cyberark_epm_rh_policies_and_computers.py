#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
rest handler file for Policies and Computers modular input
"""

import logging

# isort: off
import import_declare_test  # noqa: F401

from cyberark_epm_utils import CyberarkEpmExternalHandler
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import (  # noqa: F401
    AdminExternalHandler,
)
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator,
)

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        "account_name", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "set_ids",
        required=True,
        encrypted=False,
        default="All",
        validator=None,
    ),
    field.RestField(
        "collect_data_for", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "collect_policy_details",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "interval", required=False, encrypted=False, default=86400, validator=None
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
    "policies_and_computers",
    model,
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CyberarkEpmExternalHandler,
    )
