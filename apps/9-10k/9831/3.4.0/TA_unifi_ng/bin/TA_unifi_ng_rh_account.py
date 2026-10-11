# Copyright 2026
# SPDX-License-Identifier: Apache-2.0
#
# REST handler for the UniFi account tab (UCC pattern).
# Validates API key against the controller when an account is saved or edited.

import import_declare_test  # noqa: F401

import logging

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    RestModel,
    SingleModel,
    field,
    validator,
)
from splunktaucclib.rest_handler import admin_external, util

from unifi_ingest import UniFiApiError, _parse_bool, test_unifi_connection

util.remove_http_proxy_env_vars()

logger = logging.getLogger(__name__)

fields = [
    field.RestField(
        "controller_url",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(max_len=256, min_len=1),
    ),
    field.RestField(
        "api_key",
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(max_len=256, min_len=1),
    ),
    field.RestField(
        "verify_ssl",
        required=False,
        encrypted=False,
        default=False,
        validator=None,
    ),
]
model = RestModel(fields, name=None)
endpoint = SingleModel(
    "ta_unifi_ng_account", model, config_name="account", app="TA_unifi_ng"
)


class UniFiAccountHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        self._validate_connection()
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        self._validate_connection()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        AdminExternalHandler.handleRemove(self, confInfo)

    def _validate_connection(self):
        """Test the controller connection when the account is saved."""
        url = (self.payload.get("controller_url") or "").strip()
        api_key = (self.payload.get("api_key") or "").strip()
        verify_ssl = _parse_bool(self.payload.get("verify_ssl", "0"), default=False)

        if not url:
            raise admin_external.RestError(400, "Controller URL is required.")
        if not api_key:
            raise admin_external.RestError(400, "API Key is required.")

        try:
            result = test_unifi_connection(url, api_key, verify_ssl=verify_ssl)
            logger.info(
                "Account validation successful: %d site(s) found at %s",
                result.get("site_count", 0),
                result.get("host", url),
            )
        except UniFiApiError as e:
            raise admin_external.RestError(
                400, f"Connection test failed: {e}"
            ) from e
        except Exception as e:
            raise admin_external.RestError(
                400, f"Unexpected error during connection test: {e}"
            ) from e


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=UniFiAccountHandler,
    )
