#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import logging

import splunk_ta_o365_bootstrap
from rh_common import HostValidator
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    MultipleModel,
    RestModel,
    field,
    validator,
)

util.remove_http_proxy_env_vars()

ssl_cert_settings = [
    field.RestField(
        "ca_certs_path", required=True, encrypted=False, default="", validator=None
    )
]
model_ssl_cert_settings = RestModel(ssl_cert_settings, name="sslCertSettings")

endpoint = MultipleModel(
    "splunk_ta_o365_ssl_cert",
    models=[model_ssl_cert_settings],
)


class SSLCertRestHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleCreate(self, confInfo):
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo):
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=SSLCertRestHandler,
    )
