import import_declare_test

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

#manual imports
import sb_utils as utils
import os
import traceback
from splunktaucclib.rest_handler import util

util.remove_http_proxy_env_vars()

FILE_NAME = (os.path.basename(__file__)).split('.')[0]
CP_ID = "checkpointer"


class DeleteCheckpointExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        self.delete_checkpoint()
        AdminExternalHandler.handleRemove(self, confInfo)

    def delete_checkpoint(self):
        """
        Delete the checkpoint when user deletes input.
        """
        self.session_key = self.getSessionKey()
        self.logger = utils.set_logger(self.session_key, FILE_NAME)
        input_name = str(self.callerArgs.id)
        acessstoken_checkpoint_name = input_name + "_accesstoken"
        input_checkpoint_name = input_name + "_input"
        try:
            utils.delete_check_point(self, acessstoken_checkpoint_name, CP_ID)
            utils.delete_check_point(self, input_checkpoint_name, CP_ID)
        except Exception:
            self.logger.error(
                f"Error while deleting checkpoint for {input_name} input. {traceback.format_exc()}"
            )


