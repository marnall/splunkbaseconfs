##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test  # noqa: F401 # isort: skip
import json
import logging
import os
import sys

import splunk.rest as rest
import splunk_ta_f5_utility as common_utility
from import_declare_test import ta_name
from log_manager import setup_logging
from splunk_ta_f5_ui_validation import HECValidation, TemplateValidator
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

from splunktaucclib.rest_handler.endpoint import (  # isort: skip
    DataInputModel,
    RestModel,
    field,
    validator,
)  # isort: skip


sys.path.insert(
    0, os.path.abspath(os.path.join(__file__, "..", "modinputs", "icontrol"))
)
import collector  # noqa: E402

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "description",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255,
            min_len=0,
        ),
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=300,
        validator=validator.Number(
            min_val=300,
            max_val=10000000,
        ),
    ),
    field.RestField(
        "hec_name",
        required=True,
        encrypted=False,
        default=None,
        validator=HECValidation(),
    ),
    field.RestField(
        "splunk_host",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255,
            min_len=1,
        ),
    ),
    field.RestField(
        "servers", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "templates",
        required=True,
        encrypted=False,
        default=None,
        validator=TemplateValidator(),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "f5_task",
    model,
)


class F5TaskHandler(AdminExternalHandler):
    """
    This class handles the parameters in the configuration page
    """

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        if self.callerArgs.id:
            self.logger = setup_logging(
                self.getSessionKey(), f"splunk_ta_f5_bigip_input-{self.callerArgs.id}"
            )

    def get_input_items(self, session_key, input_value):
        input_name = "f5_task://" + str(input_value)
        input_item = {}
        try:
            response_status, response_content = rest.simpleRequest(
                "/servicesNS/nobody/" + str(ta_name) + "/configs/conf-inputs/",
                sessionKey=session_key,
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )
            res = json.loads(response_content)
            if "entry" in res:
                for inputs in res["entry"]:
                    if inputs.get("name") == input_name and inputs.get("content"):
                        content = inputs.get("content")
                        input_item["servers"] = content.get("servers")
                        input_item["templates"] = content.get("templates")
                        input_item["name"] = input_value
                        input_item["hec_name"] = content.get("hec_name")
                        input_item["interval"] = content.get("interval")
                        input_item["splunk_host"] = content.get("splunk_host")
        except Exception as e:
            self.logger.error("Error while fetching details: {}".format(e))

        return input_item

    def handleRemove(self, confInfo):
        session_key = self.getSessionKey()
        input_name = self.callerArgs.id
        input_item = self.get_input_items(session_key, input_name)
        icontrol_collector = collector.IcontrolCollector(
            session_key, input_item, "disabled", self.logger
        )
        try:
            # Make disable API Calls.
            failed_api_call = icontrol_collector.run()
        except RestError as re:
            self.logger.error(re)
            raise RestError(409, re)
        except ValueError as ve:  # noqa: F841
            self.logger.error(
                "Stopping data collection because of insufficient information. Please check if all the required fields are provided in the input."
            )
            raise RestError(
                409,
                "Stopping data collection because of insufficient information. Please check if all the required fields are provided in the input.",  # noqa: E501
            )
        if not failed_api_call:
            self.logger.info(
                "Successfully disabled the API calls. Deleting the checkpoint"
            )
            try:
                # Delete checkpoint
                common_utility.delete_checkpoint(session_key, input_name, self.logger)
                self.logger.info(
                    "Checkpoint deleted for the input: {}".format(input_name)
                )
                AdminExternalHandler.handleRemove(self, confInfo)
            except Exception as e:
                self.logger.error(
                    "Error occured while deleting checkpoint: {}".format(e)
                )
        else:
            self.logger.error(
                "Failed to execute all the api calls for delete input: {}".format(
                    failed_api_call
                )
            )
            raise RestError(
                409,
                "Failed to execute all the api calls for disable input. Please check the logs to verify which api calls were not successful",  # noqa: E501
            )

    def handleEdit(self, confInfo):
        session_key = self.getSessionKey()
        input_name = self.callerArgs.id
        input_item = self.get_input_items(session_key, input_name)
        if self.payload.get("disabled") == "true":
            icontrol_collector = collector.IcontrolCollector(
                session_key, input_item, "disabled", self.logger
            )
            self.logger.info(
                "Starting process to make disable API calls for input: {}".format(
                    input_name
                )
            )
            try:
                # Make disable API Calls.
                failed_api_call = icontrol_collector.run()
            except RestError as re:
                self.logger.error(re)
                raise RestError(409, re)
            except ValueError as ve:  # noqa: F841
                self.logger.error(
                    "Stopping data collection because of insufficient information. Please check if all the required fields are provided in the input."
                )
                raise RestError(
                    409,
                    "Stopping data collection because of insufficient information. Please check if all the required fields are provided in the input.",  # noqa: E501
                )
            if not failed_api_call:
                # Disable the input only if the api calls are successful.
                AdminExternalHandler.handleEdit(self, confInfo)
            else:
                self.logger.error(
                    "Failed to execute all the api calls for disable input: {}".format(
                        failed_api_call
                    )
                )
                raise RestError(
                    409,
                    "Failed to execute all the api calls for disable input. Please check the logs to verify which api calls were not successful",  # noqa: E501
                )
        else:
            payload = self.payload
            if input_item.get("hec_name") is None and payload.get("hec_name"):
                if input_item.get("splunk_host") is None and payload.get("splunk_host"):
                    AdminExternalHandler.handleEdit(self, confInfo)
                    return True

            icontrol_collector = collector.IcontrolCollector(
                session_key, input_item, "enabled", self.logger
            )
            checkpoint_value = icontrol_collector.run(get_checkpoint=True)
            if (
                checkpoint_value
                and checkpoint_value.get("data_collection_state") == "collecting"
            ):
                self.logger.error(
                    "Data collection is in progress. So, try again after sometime."
                )
                raise RestError(
                    409, "Data collection is in progress. So, try again after sometime."
                )
            AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=F5TaskHandler,
    )
