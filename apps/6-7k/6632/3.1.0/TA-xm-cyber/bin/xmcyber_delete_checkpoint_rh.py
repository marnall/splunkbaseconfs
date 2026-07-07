"""Module for handling deletion of XM Cyber checkpoints in Splunk."""
import import_declare_test  # noqa: F401

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from import_declare_test import ta_prefix
from log_helper import setup_logging
from xmcyber_utils import delete_checkpoint
import traceback


class DeleteCheckpointRestHandler(AdminExternalHandler):
    """Handler for deleting XM Cyber checkpoints."""

    def __init__(self, *args, **kwargs):
        """Initialize the XMCyberDeleteCheckpointHandler."""
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self.logger = setup_logging(f"{ta_prefix}_audit_trail_delete_checkpoint")

    def handleRemove(self, confinfo):
        """Delete a XM Cyber checkpoint setting."""
        try:
            input_name = str(self.callerArgs.id)
            self.logger.info(f"Deleting checkpoint for input: {input_name}")
            session_key = self.getSessionKey()
            delete_checkpoint(session_key, input_name)
            AdminExternalHandler.handleRemove(self, confinfo)
            self.logger.info(f"Successfully deleted checkpoint for input: {input_name}")
        except Exception as e:
            self.logger.error(
                f"Error while deleting checkpoint for input: {input_name}."
                f" Error: {e}  {traceback.format_exc()}"
            )
