#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import splunk_ta_o365_bootstrap

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


special_fields = [
    field.RestField(
        "name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^\w+$""",
            ),
            validator.String(
                max_len=100,
                min_len=1,
            ),
        ),
    )
]

fields = [
    field.RestField(
        "tenant_name", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "entra_id_type", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "sourcetype",
        required=True,
        encrypted=False,
        default="o365:metadata",
        validator=validator.String(
            max_len=1024,
            min_len=1,
        ),
    ),
    field.RestField(
        "query_parameters",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=8192,
                min_len=2,
            ),
            validator.Pattern(
                regex=r"""^\$""",
            ),
        ),
    ),
    field.RestField(
        "api_version", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "index", required=True, encrypted=False, default="default", validator=None
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default="86400",
        validator=validator.Pattern(
            regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""",
        ),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = DataInputModel(
    "splunk_ta_o365_microsoft_entra_id_metadata",
    model,
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
