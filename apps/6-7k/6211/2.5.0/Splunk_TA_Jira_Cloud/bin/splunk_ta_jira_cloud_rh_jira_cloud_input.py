#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import logging

import import_declare_test  # noqa
import jira_cloud_rh as rh
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator,
)
from splunk_ta_jira_cloud_input_validation import JiraAuditStartDateValidation

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "api_token", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "from",
        required=False,
        encrypted=False,
        default="",
        validator=JiraAuditStartDateValidation(),
    ),
    field.RestField(
        "use_existing_checkpoint",
        required=False,
        encrypted=False,
        default="yes",
        validator=None,
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=60,
        validator=validator.Number(
            max_val=3600,
            min_val=10,
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
    "jira_cloud_input",
    model,
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=rh.JiraCloudExternalHandler,
    )
