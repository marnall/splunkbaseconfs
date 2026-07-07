#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""

* isort ignores:
- isort: skip = Should not be sorted.
* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
- noqa: E501 -> Def = line too long
    Reason for ignoring = Can't split into 2 lines
"""

import splunk_ta_remedy_declare  # isort: skip # noqa: F401

import logging
import os
from datetime import datetime, timedelta

from solnlib.modular_input import FileCheckpointer
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunk_ta_remedy_input_checkpoint import KVCheckpointHandler
from remedy_consts import CHECKPOINT_COLLECTION_NAME
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator,
)


util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "account", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=60,
        validator=validator.AllOf(
            validator.Number(
                max_val=31536000,
                min_val=1,
            ),
            validator.Pattern(
                regex=r"""^\d+$""",
            ),
        ),
    ),
    field.RestField(
        "form_type", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "form_name", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "include_properties",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[\w\s-]+(,[\w\s]+)*$""",
        ),
    ),
    field.RestField(
        "exclude_properties",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[\w\s-]+(,[\w\s]+)*$""",
        ),
    ),
    field.RestField(
        "timefield",
        required=True,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "reuse_checkpoint",
        required=False,
        encrypted=False,
        default="yes",
        validator=None,
    ),
    field.RestField(
        "query_start_date",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(0[1-9]|1[012])/(0[1-9]|[12][0-9]|3[01])/([0-9]{4})\s([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9])$""",  # noqa: E501
        ),
    ),
    field.RestField(
        "qualification", required=False, encrypted=False, default=None, validator=None
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
    "remedy_input",
    model,
)


class RemedyInputHandler(AdminExternalHandler):
    """
    Manage Snow Data Input Details.
    """

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self.session_key = self.getSessionKey()

    def deleteCheckpoint(self, kv_checkpoint_key_name):
        ckpt_manager = KVCheckpointHandler(
            CHECKPOINT_COLLECTION_NAME, self.session_key, kv_checkpoint_key_name
        )
        ckpt_manager.file_checkpointer.delete(ckpt_manager.input_name)
        ckpt_manager.delete_kv_checkpoint()

    def checkReuseCheckpoint(self):
        # Check the reuse_checkpoint field. If it's value is 'no', delete it's checkpoint if present.
        if self.payload.get("reuse_checkpoint") == "no":
            # kv checkpoint key has been updated to combination of inputname.form_name.timefield, hence creating the combination
            ckpt_name = f"{self.callerArgs.id}.{self.payload.get('form_name')}.{self.payload.get('timefield')}"
            self.deleteCheckpoint(ckpt_name)

        if "reuse_checkpoint" in self.payload:
            del self.payload["reuse_checkpoint"]

    def checkQueryStartDate(self):
        now = datetime.utcnow() - timedelta(7)
        # Check if query_start_date field is empty.
        # If so, set its default value to one week ago so that it gets reflected in UI.
        if not self.payload.get("query_start_date"):
            self.payload["query_start_date"] = datetime.strftime(
                now, "%m/%d/%Y %H:%M:%S"
            )

    def handleCreate(self, confInfo):
        self.checkReuseCheckpoint()
        self.checkQueryStartDate()

        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo):
        self.checkReuseCheckpoint()
        self.checkQueryStartDate()

        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=RemedyInputHandler,
    )
