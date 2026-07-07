#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

# isort: off
import import_declare_test  # noqa: F401

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from cyberark_epm_utils import CyberarkEpmExternalHandler
import logging

from splunk_TA_cyberark_epm_start_date_validation import StartDateValidation
from splunk_ta_cyberark_epm_account_validation import AccountNameValidation

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "account_name",
        required=True,
        encrypted=False,
        default=None,
        validator=AccountNameValidation(),
    ),
    field.RestField(
        "set_ids",
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
        "interval",
        required=True,
        encrypted=False,
        default=360,
        validator=validator.AllOf(
            validator.Number(
                max_val=3600,
                min_val=360,
            ),
            validator.Pattern(
                regex=r"""^\d+$""",
            ),
        ),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.AllOf(
            validator.String(
                max_len=80,
                min_len=1,
            ),
            validator.Pattern(
                regex=r"""^[^_].*$""",
            ),
        ),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "admin_audit_logs",
    model,
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CyberarkEpmExternalHandler,
    )
