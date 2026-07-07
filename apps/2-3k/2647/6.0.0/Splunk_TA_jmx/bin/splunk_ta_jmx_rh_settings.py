#
# SPDX-FileCopyrightText: 2026 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#

import import_declare_test  # isort: skip # noqa: F401
import logging

from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    MultipleModel,
    RestModel,
    field,
    validator,
)

util.remove_http_proxy_env_vars()


fields_logging = [
    field.RestField(
        "loglevel", required=True, encrypted=False, default="INFO", validator=None
    )
]
model_logging = RestModel(fields_logging, name="logging")

fields_general = [
    field.RestField(
        "display_destination_app",
        required=False,
        encrypted=False,
        default=True,
        validator=None,
    )
]
model_general = RestModel(fields_general, name="general")

fields_java_props = [
    field.RestField(
        "ts_password", required=False, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "ks_password", required=False, encrypted=True, default=None, validator=None
    ),
    field.RestField(
        "cert_length",
        required=False,
        encrypted=False,
        default=10,
        validator=validator.Number(max_val=1000, min_val=1, is_int=True),
    ),
]
model_java_props = RestModel(fields_java_props, name="java_sys_prop")

endpoint = MultipleModel(
    "splunk_ta_jmx_settings",
    models=[model_logging, model_general, model_java_props],
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
