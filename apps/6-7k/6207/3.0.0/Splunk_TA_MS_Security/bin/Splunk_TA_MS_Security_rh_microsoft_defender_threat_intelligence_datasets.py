##
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test  # noqa: F401 isort: skip

from splunktaucclib.rest_handler import admin_external, util
import logging

from splunk_ta_mscs.app.mdti.rest_model import endpoint
from splunk_ta_mscs.app.mdti.rest_handler import MDTIInputHandler

util.remove_http_proxy_env_vars()


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint=endpoint,
        handler=MDTIInputHandler,
    )
