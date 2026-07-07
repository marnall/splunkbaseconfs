import import_declare_test

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

#manual imports
import sb_utils as utils
import os
import traceback
from sblv.sb_validation import LV
from splunktaucclib.rest_handler import util
util.remove_http_proxy_env_vars()

FILE_NAME = (os.path.basename(__file__)).split('.')[0]
CP_ID = "l_info"

class lV(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def _callValidator(self):
        LV(session_key=self.getSessionKey()).validate_l(
            app_id="2",
            l_key=self.payload.get("licensekey"),
            license_proxy_enabled=self.payload.get("license_proxy_enabled"), 
            license_name= str(self.callerArgs.id)
        )

    def handleEdit(self, confInfo):
        self._callValidator()
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        self._callValidator()
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
        l_info_checkpoint_name = input_name + "_l_info"
        try:
            utils.delete_check_point(self, l_info_checkpoint_name, CP_ID)
        except Exception:
            self.logger.error(
                f"Error while deleting checkpoint for {input_name} input. {traceback.format_exc()}"
            )
