import import_declare_test

from splunktaucclib.rest_handler import util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from sblv.sb_validation import LV

util.remove_http_proxy_env_vars()

class lV(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def _callValidator(self):
        LV(session_key=self.getSessionKey()).validate_l(
            app_id="1",
            l_key=self.payload.get("licensekey"),
            license_proxy_enabled=self.payload.get("license_proxy_enabled"),
        )

    def handleEdit(self, confInfo):
        self._callValidator()
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        self._callValidator()
        AdminExternalHandler.handleCreate(self, confInfo) 

    def handleRemove(self, confInfo):
        AdminExternalHandler.handleRemove(self, confInfo)
