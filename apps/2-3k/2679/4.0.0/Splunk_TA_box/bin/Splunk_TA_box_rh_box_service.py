#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # isort: skip # noqa: F401
import logging
import traceback
from datetime import datetime, timedelta

import box_utility
from checkpoint import Checkpointer
from solnlib import conf_manager, log, utils
from solnlib.splunkenv import make_splunkhome_path
from Splunk_TA_box_input_validation import DateValidator
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator,
)

_LOGGER = log.Logs().get_logger("ta_box")

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        "input_name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^([a-zA-Z]\w*)$""",
        ),
    ),
    field.RestField(
        "account", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "rest_endpoint",
        required=True,
        encrypted=False,
        default="events",
        validator=None,
    ),
    field.RestField(
        "collect_folder", required=False, encrypted=False, default=1, validator=None
    ),
    field.RestField(
        "collect_collaboration",
        required=False,
        encrypted=False,
        default=1,
        validator=None,
    ),
    field.RestField(
        "collect_file", required=False, encrypted=False, default=1, validator=None
    ),
    field.RestField(
        "collect_task", required=False, encrypted=False, default=1, validator=None
    ),
    field.RestField(
        "created_after",
        required=False,
        encrypted=False,
        default=None,
        validator=DateValidator(),
    ),
    field.RestField(
        "duration",
        required=False,
        encrypted=False,
        default="Deprecated - Please use the interval field instead",
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=120,
        validator=validator.Number(min_val=1, max_val=31536000, is_int=True),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.String(
            min_len=1,
            max_len=80,
        ),
    ),
    field.RestField(
        "folder_fields", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "file_fields", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "task_fields", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "comment_fields", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "user_fields", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "reuse_checkpoint",
        required=False,
        encrypted=False,
        default="no",
    ),
    field.RestField("disabled", required=False, validator=None),
    field.RestField(
        "event_delay",
        required=False,
        encrypted=False,
        default="0",
        validator=validator.Pattern(
            regex=r"""^[1-9]\d*$|^\d*$""",
        ),
    ),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "box_service",
    model,
)


class BoxServiceHandler(AdminExternalHandler):
    """
    Manage Box Data Input Details.
    """

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        cfm = conf_manager.ConfManager(
            self.getSessionKey(),
            "Splunk_TA_box",
            realm="__REST_CREDENTIAL__#Splunk_TA_box#configs/conf-splunk_ta_box_settings",
        )
        logging = cfm.get_conf("splunk_ta_box_settings").get("logging")
        _LOGGER.setLevel(logging.get("loglevel", "INFO"))

    @staticmethod
    def get_session_key(self):
        return self.getSessionKey()

    # jscpd:ignore-start
    def deleteCheckpoint(self, input_name, rest_endpoint_value):
        session_key = self.get_session_key(self)
        collection_name = import_declare_test.COLLECTION_VALUE_FROM_ENDPOINT.get(
            rest_endpoint_value
        )
        checkpoint_dir = make_splunkhome_path(
            ["var", "lib", "splunk", "modinputs", "box_service"]
        )
        use_state_store = True
        box_utility.delete_existing_checkpoint(
            input_name,
            use_state_store,
            session_key,
            checkpoint_dir,
            collection_name,
            _LOGGER,
        )

    def updateTimestamp(self, input_name, rest_endpoint_value, timestamp):
        session_key = self.get_session_key(self)
        use_state_store = True
        checkpoint_dir = make_splunkhome_path(
            ["var", "lib", "splunk", "modinputs", "box_service"]
        )
        collection_name = import_declare_test.COLLECTION_VALUE_FROM_ENDPOINT.get(
            rest_endpoint_value
        )
        try:
            checkpointer_object = Checkpointer(
                session_key, input_name, collection_name, _LOGGER
            )
            (
                kv_checkpoint_exist,
                kv_checkpoint_value,
            ) = checkpointer_object.check_for_kv_checkpoint()
            (
                file_checkpoint_exist,
                file_checkpoint_value,
            ) = checkpointer_object.check_for_file_checkpoint(
                use_state_store, checkpoint_dir
            )
            if kv_checkpoint_exist and kv_checkpoint_value:
                kv_checkpoint_value["start_timestamp"] = timestamp
                checkpointer_object.update_kv_checkpoint(kv_checkpoint_value)
            elif file_checkpoint_exist and file_checkpoint_value:
                file_checkpoint_value["start_timestamp"] = timestamp
                checkpointer_object.update_file_checkpoint(
                    file_checkpoint_value, checkpoint_dir
                )
        except Exception as e:
            _LOGGER.error(
                "Error occured while updating the start_timestamp for the input: {}:{}".format(
                    input_name, e
                )
            )

    # jscpd:ignore-end

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)
        # when input page reload if input is disabled, update start_timestamp to 0
        # which starts data collection when input is enabled
        for inputStanzaKey, inputStanzaValue in list(confInfo.items()):
            rest_endpoint_value = inputStanzaValue.get("rest_endpoint")
            if utils.is_true(inputStanzaValue.get("disabled")):
                self.updateTimestamp(inputStanzaKey, rest_endpoint_value, 0)

            # If migration is not yet done, display duration field value instead of interval on the inputs page.
            if inputStanzaValue.get("duration"):
                if (
                    inputStanzaValue["duration"]
                    != "Deprecated - Please use the interval field instead"
                ):
                    try:
                        duration = int(inputStanzaValue["duration"])
                        inputStanzaValue["interval"] = str(duration)
                    except ValueError:
                        # do not show duration in UI if it is not an integer
                        pass

    def checkCreatedAfter(self):
        quarter_ago = datetime.utcnow() - timedelta(days=90)
        quarter_ago = datetime.strftime(quarter_ago, "%Y-%m-%dT%H:%M:%S")

        # Check if created_after field is empty. If so, set its default value to 90 days ago so that it reflects on UI.
        if (
            not self.payload.get("created_after")
            and self.payload.get("rest_endpoint") == "events"
        ):
            self.payload["created_after"] = quarter_ago

    # jscpd:ignore-start
    def handleCreate(self, confInfo):
        disabled = self.payload.get("disabled")
        rest_endpoint_value = self.payload.get("rest_endpoint")
        self.checkCreatedAfter()
        if disabled is None and self.payload.get("reuse_checkpoint") == "no":
            input_name = self.payload.get("input_name")
            reuse_checkpoint = self.payload.get("reuse_checkpoint")
            if reuse_checkpoint == "no":
                _LOGGER.info(
                    "The reuse_checkpoint field is found to be No for input {}, Hence the existing "
                    "checkpoint will be deleted and the Data will be ingested using stream "
                    "position 0.".format(input_name)
                )
                self.deleteCheckpoint(input_name, rest_endpoint_value)

        if "reuse_checkpoint" in self.payload:
            del self.payload["reuse_checkpoint"]
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo):
        disabled = self.payload.get("disabled")
        self.checkCreatedAfter()
        input_name = self.callerArgs.id
        rest_endpoint_value = self.get_endpoint_value(input_name)

        # to handle the editting of inputs which are in disabled state and not yet migrated.
        self.payload["duration"] = "Deprecated - Please use the interval field instead"

        # when input is disabled, update start_timestamp to 0
        # which starts data collection when input is enabled
        if rest_endpoint_value:
            if utils.is_true(disabled):
                self.updateTimestamp(self.callerArgs.id, rest_endpoint_value, 0)
            if disabled is None and self.payload.get("reuse_checkpoint") == "no":
                input_name = self.payload.get("input_name")
                reuse_checkpoint = self.payload.get("reuse_checkpoint")
                if reuse_checkpoint == "no":
                    _LOGGER.info(
                        "The reuse_checkpoint field is found to be No for input {}, Hence the existing "
                        "checkpoint will be deleted and the Data will be ingested using stream "
                        "position 0.".format(input_name)
                    )
                    self.deleteCheckpoint(input_name, rest_endpoint_value)

        # jscpd:ignore-end
        if "reuse_checkpoint" in self.payload:
            del self.payload["reuse_checkpoint"]
        AdminExternalHandler.handleEdit(self, confInfo)

    def get_endpoint_value(self, input_name):
        stanza_input_value = "".join(["box_service://", input_name])
        try:
            input_cfm = conf_manager.ConfManager(
                self.getSessionKey(),
                "Splunk_TA_box",
                realm="__REST_CREDENTIAL__#Splunk_TA_box#configs/conf-inputs",
            )
            input_details = input_cfm.get_conf("inputs").get(stanza_input_value)
            rest_endpoint_value = input_details.get("rest_endpoint")
            return rest_endpoint_value
        except Exception as e:
            _LOGGER.error(
                "Error occured while getting rest endpoint value: {}".format(
                    traceback.format_exc()
                )
            )
            return None


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=BoxServiceHandler,
    )
