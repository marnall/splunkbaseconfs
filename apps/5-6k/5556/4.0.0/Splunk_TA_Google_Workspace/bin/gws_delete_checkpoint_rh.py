#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import logging
import traceback

import import_declare_test  # noqa: 401
from solnlib import log
from splunktaucclib.rest_handler import admin_external

import gws_utils
from gws_utils import APP_NAME
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import binding
from splunklib import client


class GwsDeleteCheckpointExternalHandler(admin_external.AdminExternalHandler):
    """
    This class extends the functionality of the basic rest handler available in
    the add-on by including deletion of the checkpoints (file-based for
    activity_report and KVStore-based for gws_gmail_logs).
    """

    def __init__(self, *args, **kwargs):
        admin_external.AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, conf_info):
        # Wrap the parent handleList so that a missing or unreachable KVStore
        # checkpoint collection (which causes the UCC handler.all() call to return
        # HTTP 404) does not propagate as an uncaught RestError and break the
        # Inputs page with a "Not Found" error.
        try:
            admin_external.AdminExternalHandler.handleList(self, conf_info)
        except Exception as e:
            log.log_exception(
                log.Logs().get_logger("splunk_ta_google_workspace_delete_checkpoint"),
                e,
                "List Error",
                msg_before=(
                    "handleList encountered an unexpected error — the Inputs page may "
                    "display 'Not Found'. This is often caused by a missing or "
                    "unreachable KVStore checkpoint collection. Check KVStore status "
                    "at /services/kvstore/status and verify all "
                    "activity_report_checkpoint_* collections exist for this add-on."
                ),
            )

    def handleEdit(self, conf_info):
        admin_external.AdminExternalHandler.handleEdit(self, conf_info)

    def handleCreate(self, conf_info):
        admin_external.AdminExternalHandler.handleCreate(self, conf_info)

    def handleRemove(self, conf_info):
        self.delete_checkpoint()
        admin_external.AdminExternalHandler.handleRemove(self, conf_info)

    def _delete_collection(
        self, logger: logging.Logger, service: client.Service, collection_name: str
    ):
        try:
            service.kvstore.delete(collection_name)
            logger.info(f"Removed KVStore collection '{collection_name}'")
        except binding.HTTPError as e:
            log.log_exception(
                logger,
                e,
                "Checkpoint Error",
                msg_before=f"Could not delete the KVStore collection '{collection_name}'",
            )
        except Exception as e:
            # KVStore can drop the connection (SSL handshake failure, RemoteDisconnected,
            # urllib3 ProtocolError, etc.). Those raise outside of binding.HTTPError and
            # would otherwise bubble out of the REST handler and surface as a "Not Found"
            # in the add-on Inputs UI. Swallow them with an actionable log
            # so input deletion can still proceed.
            log.log_exception(
                logger,
                e,
                "Checkpoint Error",
                msg_before=(
                    f"KVStore communication error while deleting collection "
                    f"'{collection_name}'. Continuing with input removal. "
                    f"Check KVStore status at /services/kvstore/status."
                ),
            )

    def _delete_checkpoint_for_activity_report(
        self, logger: logging.Logger, session_key: str, input_name: str
    ):
        try:
            cf_manager = conf_manager.ConfManager(session_key, APP_NAME)
            checkpoint_conf = cf_manager.get_conf("gws_checkpoints")
            checkpoint_conf.delete(f"activity_report:__{input_name}")
            logger.info(
                f"Removed file-based checkpoint for activity_report:{input_name} input"
            )
        except conf_manager.ConfManagerException as e:
            log.log_exception(
                logger,
                e,
                "Checkpoint Error",
                msg_before="No gws_checkpoints file found",
            )
        except conf_manager.ConfStanzaNotExistException as e:
            log.log_exception(
                logger,
                e,
                "Checkpoint Error",
                msg_before=f"No stanza activity_report:__{input_name} in gws_checkpoint file",
            )
        checkpoint_collection_name = (
            gws_utils.get_activity_report_checkpoint_collection_name_from_input_name(
                input_name
            )
        )
        unsuccessful_runs_collection_name = gws_utils.get_activity_report_unsuccessful_runs_collection_name_from_input_name(
            input_name
        )
        try:
            service = client.connect(app=APP_NAME, token=session_key)
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Checkpoint Error",
                msg_before=(
                    f"Could not connect to splunkd to delete KVStore checkpoints for "
                    f"'{input_name}'. Skipping checkpoint cleanup; input removal will "
                    f"still proceed."
                ),
            )
            return
        self._delete_collection(
            logger,
            service,
            checkpoint_collection_name,
        )
        self._delete_collection(
            logger,
            service,
            unsuccessful_runs_collection_name,
        )

    def _delete_checkpoint_for_gmail_logs(
        self, logger: logging.Logger, session_key: str, input_name: str
    ):
        normalized_input_name = input_name.split("/")[-1]
        collection_name = f"splunk_ta_google_workspace_gmail_{normalized_input_name}"
        try:
            checkpointer_service = checkpointer.KVStoreCheckpointer(
                collection_name,
                session_key,
                APP_NAME,
            )
            checkpointer_service.delete("gmail_headers_modular_input")
            logger.info(f"Removed KVStore checkpoint for {collection_name}")
        except binding.HTTPError as e:
            log.log_exception(
                logger,
                e,
                "Checkpoint Error",
                msg_before=f'Could not delete the checkpoint "splunk_ta_google_workspace_gmail_{normalized_input_name}"',
            )
        except Exception as e:
            # See note in _delete_collection: catch any SDK / connection error so the
            # REST handler does not break the Inputs UI.
            log.log_exception(
                logger,
                e,
                "Checkpoint Error",
                msg_before=(
                    f"KVStore error while deleting gmail checkpoint "
                    f"'{collection_name}'. Continuing with input removal."
                ),
            )

    def _delete_checkpoint_for_alert_center(
        self, logger: logging.Logger, session_key: str, input_name: str
    ):
        normalized_input_name = input_name.split("/")[-1]
        collection_name = f"splunk_ta_google_workspace_alerts_{normalized_input_name}"
        try:
            checkpointer_service = checkpointer.KVStoreCheckpointer(
                collection_name,
                session_key,
                APP_NAME,
            )
            checkpointer_service.delete("gws_alerts_modular_input")
            logger.info(f"Removed KVStore checkpoint for {collection_name}")
        except binding.HTTPError as e:
            log.log_exception(
                logger,
                e,
                "Checkpoint Error",
                msg_before=f'Could not delete the checkpoint "splunk_ta_google_workspace_alerts_{normalized_input_name}"',
            )
        except Exception as e:
            # See note in _delete_collection: catch any SDK / connection error so the
            # REST handler does not break the Inputs UI.
            log.log_exception(
                logger,
                e,
                "Checkpoint Error",
                msg_before=(
                    f"KVStore error while deleting alert center checkpoint "
                    f"'{collection_name}'. Continuing with input removal."
                ),
            )

    def delete_checkpoint(self):
        """
        Delete the checkpoint when user deletes input.
        """
        log_filename = "splunk_ta_google_workspace_delete_checkpoint"
        logger = log.Logs().get_logger(log_filename)
        input_name = str(self.callerArgs.id)
        input_type = self.handler.get_endpoint().input_type
        session_key = self.getSessionKey()
        try:
            if input_type == "activity_report":
                self._delete_checkpoint_for_activity_report(
                    logger,
                    session_key,
                    input_name,
                )
            if input_type == "gws_gmail_logs":
                self._delete_checkpoint_for_gmail_logs(
                    logger,
                    session_key,
                    input_name,
                )
            if input_type == "gws_alert_center":
                self._delete_checkpoint_for_alert_center(
                    logger,
                    session_key,
                    input_name,
                )
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Checkpoint Error",
                msg_before=f"Error while deleting checkpoint for {input_name} input. {traceback.format_exc()}",
            )
