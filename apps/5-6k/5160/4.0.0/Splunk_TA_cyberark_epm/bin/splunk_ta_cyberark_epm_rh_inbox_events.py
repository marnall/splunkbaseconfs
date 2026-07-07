#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
rest handler file for Inbox Events modular input
"""

import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)

from cyberark_epm_utils import CyberarkEpmExternalHandler
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunk_TA_cyberark_epm_start_date_validation import StartDateValidation
import logging

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
        "publisher",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[^<>]+$""",
        ),
    ),
    field.RestField(
        "justification", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "application_type",
        required=True,
        encrypted=False,
        default="All",
        validator=None,
    ),
    field.RestField(
        "use_existing_checkpoint",
        required=False,
        encrypted=False,
        default="yes",
        validator=None,
    ),
    field.RestField(
        "start_date",
        required=False,
        encrypted=False,
        default=None,
        validator=StartDateValidation(),
    ),
    field.RestField(
        "api_type", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=360,
        validator=validator.Number(max_val=31536000, min_val=1, is_int=True),
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
    "inbox_events",
    model,
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CyberarkEpmExternalHandler,
    )
