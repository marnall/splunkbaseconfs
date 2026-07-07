#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
rest handler file for Policy Audit modular input
"""

import logging

# isort: off
import import_declare_test  # noqa: F401

from old_cyberark_epm_utils import CyberarkEpmExternalHandler
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
        "publisher",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=500,
        ),
    ),
    field.RestField(
        "policy_name",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=500,
        ),
    ),
    field.RestField(
        "justification", required=True, encrypted=False, default="All", validator=None
    ),
    field.RestField(
        "application_type",
        required=True,
        encrypted=False,
        default="All",
        validator=None,
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=60,
        validator=validator.Number(
            max_val=31536000,
            min_val=1,
        ),
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
    "policy_audit",
    model,
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CyberarkEpmExternalHandler,
    )
