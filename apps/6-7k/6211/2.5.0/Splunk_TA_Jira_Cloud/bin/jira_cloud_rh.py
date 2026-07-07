#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import os
from splunk import ResourceNotFound
import splunk.rest as rest
from solnlib import log
from splunktaucclib.rest_handler import admin_external
from splunktaucclib.rest_handler.error import RestError
from jira_cloud_utils import add_ucc_error_logger
import jira_cloud_consts as jcc

APP_NAME = __file__.split(os.path.sep)[-3]


class JiraCloudExternalHandler(admin_external.AdminExternalHandler):
    """
    This class contains methods related to Checkpointing
    """

    def __init__(self, *args, **kwargs):
        admin_external.AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, conf_info):
        admin_external.AdminExternalHandler.handleList(self, conf_info)

    def handleEdit(self, conf_info):
        if self.payload.get("use_existing_checkpoint") == "no":
            self.delete_checkpoint()
        if "use_existing_checkpoint" in self.payload:
            del self.payload["use_existing_checkpoint"]
        admin_external.AdminExternalHandler.handleEdit(self, conf_info)

    def handleCreate(self, conf_info):
        if "use_existing_checkpoint" in self.payload:
            del self.payload["use_existing_checkpoint"]
        admin_external.AdminExternalHandler.handleCreate(self, conf_info)

    def handleRemove(self, conf_info):
        self.delete_checkpoint()
        admin_external.AdminExternalHandler.handleRemove(self, conf_info)

    def delete_checkpoint(self):
        """
        Delete the checkpoint when user deletes input
        """
        log_filename = "splunk_ta_jira_cloud_delete_checkpoint"
        logger = log.Logs().get_logger(log_filename)
        try:
            session_key = self.getSessionKey()
            input_type = self.handler.get_endpoint().input_type
            input_types = [
                "jira_cloud_input",
            ]
            if input_type in input_types:
                checkpoint_name = input_type + "_" + str(self.callerArgs.id)
                rest_url = (
                    "/servicesNS/nobody/{}/storage/collections/config/{}/".format(
                        APP_NAME, checkpoint_name
                    )
                )
                _, _ = rest.simpleRequest(
                    rest_url,
                    sessionKey=session_key,
                    method="DELETE",
                    getargs={"output_mode": "json"},
                    raiseAllErrors=True,
                )

                logger.info(
                    "Removed checkpoint for {} input".format(str(self.callerArgs.id))
                )
        except ResourceNotFound:
            logger.info(
                "No checkpoint collection found for the input: {}".format(
                    self.callerArgs.id
                )
            )
        except Exception as e:
            msg = "Error while deleting checkpoint for {} input. Error: {}".format(
                str(self.callerArgs.id), str(e)
            )
            add_ucc_error_logger(
                logger,
                jcc.GENERAL_EXCEPTION,
                e,
                exc_label=f"{self.handler.get_endpoint().input_type}_{self.callerArgs.id}",
                msg_before=msg,
            )
            raise RestError(
                500,
                "Error while deleting checkpoint for {} input.".format(
                    self.callerArgs.id
                ),
            )
