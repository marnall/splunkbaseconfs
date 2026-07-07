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
from splunktaucclib.rest_handler.error import RestError
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging

from rh_common import graph_api_list_remove_item
from rh_common import GraphAPIAuditLogsStartDateValidator

util.remove_http_proxy_env_vars()

CONTENT_TYPES = ["AuditLogs.SignIns"]


fields = [
    field.RestField(
        "tenant_name", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "content_type", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "start_date",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "index", required=True, encrypted=False, default="default", validator=None
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default="300",
        validator=validator.Pattern(
            regex=r"""^\d+$""",
        ),
    ),
    field.RestField(
        "request_timeout",
        required=False,
        encrypted=False,
        default="60",
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[1-9]\d*$""",
            ),
            validator.Number(
                max_val=600,
                min_val=10,
            ),
        ),
    ),
    field.RestField(
        "query_window_size",
        required=False,
        encrypted=False,
        default="60",
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[1-9]\d*$""",
            ),
            validator.Number(
                max_val=1440,
                min_val=1,
            ),
        ),
    ),
    field.RestField(
        "delay_throttle_min",
        required=False,
        encrypted=False,
        default="0",
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[0-9]\d*$""",
            ),
            validator.Number(
                max_val=1440,
                min_val=0,
            ),
        ),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "splunk_ta_o365_graph_api",
    model,
)


class AuditLogsInputRestHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

        graph_api_list_remove_item(confInfo, CONTENT_TYPES)

    def handleCreate(self, confInfo):
        query_window_size = self.payload.get("query_window_size")
        request_timeout = self.payload.get("request_timeout")
        if not query_window_size:
            self.payload["query_window_size"] = "60"
        if not request_timeout:
            self.payload["request_timeout"] = "60"

        validator = GraphAPIAuditLogsStartDateValidator()
        result, message = validator.validate(self.payload)
        if not result:
            raise RestError(400, message)

        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo):
        query_window_size = self.payload.get("query_window_size")
        request_timeout = self.payload.get("request_timeout")
        if not query_window_size:
            self.payload["query_window_size"] = "60"
        if not request_timeout:
            self.payload["request_timeout"] = "60"
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AuditLogsInputRestHandler,
    )
