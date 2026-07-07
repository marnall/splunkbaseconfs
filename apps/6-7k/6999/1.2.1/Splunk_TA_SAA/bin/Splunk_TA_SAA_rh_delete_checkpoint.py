"""
This module contains a custom REST handler to delete the
checkpoint associated with an input after its deletion
"""

import import_declare_test  # noqa: F401

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from saa_consts import ADDON_NAME
from solnlib.modular_input import checkpointer
from solnlib import log
from splunklib import binding


class JobsInputDeleteCheckpoint(AdminExternalHandler):
    """Handler that is used to delete the input checkpoint on input deletetion"""

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        # Add your code here to delete the checkpoint!

        self.delete_checkpoint()
        AdminExternalHandler.handleRemove(self, confInfo)

    def delete_checkpoint(self):
        """Deletes the checkpoint associated with the deleted input"""

        input_name = str(self.callerArgs.id)
        session_key = self.getSessionKey()
        log_filename = "Splunk_TA_SAA_delete_checkpoint"
        logger = log.Logs().get_logger(log_filename)

        normalized_input_name = input_name.rsplit("/", maxsplit=1)[-1]

        checkpoint_collection = "Splunk_TA_SAA_checkpointer"
        checkpoint_name = f"saa_jobs_modular_input_{normalized_input_name}"

        try:
            checkpointer_service = checkpointer.KVStoreCheckpointer(
                checkpoint_collection,
                session_key,
                ADDON_NAME,
            )
            checkpointer_service.delete(checkpoint_name)
            logger.info(f"Removed KVStore checkpoint for {checkpoint_collection}")
        except binding.HTTPError:
            logger.error(f'Could not delete the checkpoint "Splunk_TA_SAA{normalized_input_name}"')
