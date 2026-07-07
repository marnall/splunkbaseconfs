from splunktaucclib.rest_handler.admin_external import AdminExternalHandler, get_splunkd_endpoint
from splunktaucclib.splunk_aoblib.setup_util import Setup_Util


class BaseRestHandler(AdminExternalHandler):
    """
    Base handler that handles setting the `index` config on inputs.

    :param confInfo
    """

    def handleCreate(self, confInfo):
        self._set_default_index()
        super().handleCreate(confInfo)

    def handleEdit(self, confInfo):
        self._set_default_index()
        super().handleEdit(confInfo)

    def _set_default_index(self):
        # Keep per-input index when explicitly provided.
        if self.payload.get("index"):
            return

        util = Setup_Util(
            get_splunkd_endpoint(),
            self.getSessionKey(),
        )
        index = util.get_customized_setting("index")
        if index:
            self.payload["index"] = index
