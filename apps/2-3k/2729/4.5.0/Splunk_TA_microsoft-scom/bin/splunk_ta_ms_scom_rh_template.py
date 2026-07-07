#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
Rest handler file for the scom templates.

* isort ignores:
- isort: skip = Should not be sorted.

* flake8 ignores:
- noqa: E401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path

"""


import import_declare_test  # isort: skip # noqa: F401

import logging

from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import RestModel, SingleModel, field

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "description", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "content", required=True, encrypted=False, default=None, validator=None
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("microsoft_scom_templates", model, config_name="template")


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
