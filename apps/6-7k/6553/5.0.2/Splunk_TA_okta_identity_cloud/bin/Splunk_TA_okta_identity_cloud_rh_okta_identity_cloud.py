#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import logging
import datetime

import import_declare_test  # noqa
import splunk.rest as rest
import okta_utils as utils
from solnlib import log
from constant import *
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from Splunk_TA_okta_identity_cloud_date_validation import (
    StartDateValidation,
    EndDateValidation,
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
        "interval",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Number(max_val=86400, min_val=60, is_int=True),
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
    field.RestField(
        "metric", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "global_account", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "logs_delay", required=True, encrypted=False, default=30, validator=None
    ),
    field.RestField(
        "query_window_size",
        required=True,
        encrypted=False,
        default=QUERY_WINDOW_SIZE,
        validator=validator.Number(
            max_val=86400,
            min_val=300,
        ),
    ),
    field.RestField(
        "advanced_settings",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "fetch_stats",
        required=False,
        encrypted=False,
        default=True,
        validator=None,
    ),
    field.RestField("disabled", required=False, validator=None),
    field.RestField(
        "start_date",
        required=True,
        encrypted=False,
        default=DEFAULT_FALLBACK_DATE,
        validator=StartDateValidation(),
    ),
    field.RestField(
        "end_date",
        required=False,
        encrypted=False,
        default=None,
        validator=EndDateValidation(),
    ),
    field.RestField(
        "use_existing_checkpoint",
        required=False,
        encrypted=False,
        default="yes",
        validator=None,
    ),
    field.RestField(
        "collect_uris",
        required=False,
        encrypted=False,
        default=1,
        validator=None,
    ),
]


model = RestModel(fields, name=None)
endpoint = DataInputModel(
    "okta_identity_cloud",
    model,
)


class OKTAIdentityCloudExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        log_filename = "splunk_ta_okta_identity_cloud_checkpoint"
        self.logger = log.Logs().get_logger(log_filename)
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, conf_info):
        AdminExternalHandler.handleList(self, conf_info)

    def handleEdit(self, conf_info):
        """
        Don't save advanced_settings & use_existing_checkpoint in conf file
        """
        # delete checkpoint if user want to reset checkpoint in edit mode
        if self.payload.get("use_existing_checkpoint") == "no":
            self.delete_checkpoint()
        if "use_existing_checkpoint" in self.payload:
            self.payload.pop("use_existing_checkpoint", None)
        if self.payload.get("advanced_settings"):
            self.payload.pop("advanced_settings", None)
        if self.payload.get("metric") != "groups":
            self.payload.pop("fetch_stats", None)

        AdminExternalHandler.handleEdit(self, conf_info)

    def handleCreate(self, conf_info):
        """
        Don't save advanced_settings & use_existing_checkpoint in conf file
        """
        if "use_existing_checkpoint" in self.payload:
            self.payload.pop("use_existing_checkpoint", None)
        if self.payload.get("advanced_settings"):
            self.payload.pop("advanced_settings", None)
        if self.payload.get("metric") != "groups":
            self.payload.pop("fetch_stats", None)
        AdminExternalHandler.handleCreate(self, conf_info)

    def handleRemove(self, conf_info):
        self.delete_checkpoint()
        AdminExternalHandler.handleRemove(self, conf_info)

    def delete_checkpoint(self):
        """
        Delete the checkpoint when user deletes input
        """
        try:
            session_key = self.getSessionKey()
            app_name = self.handler.get_endpoint().app
            checkpoint_name = f"{app_name}_checkpoints"
            collection_name = f"{self.callerArgs.id}_checkpoints"
            rest_url = f"/servicesNS/nobody/{app_name}/storage/collections/data/{checkpoint_name}/{collection_name}"
            _, _ = rest.simpleRequest(
                rest_url,
                sessionKey=session_key,
                method="DELETE",
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )

            self.logger.info(f"Removed checkpoint for {self.callerArgs.id} input")
        except Exception as e:
            self.logger.error(
                f"Error while deleting checkpoint for {self.callerArgs.id} input. Error: {e}"
            )


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=OKTAIdentityCloudExternalHandler,
    )
