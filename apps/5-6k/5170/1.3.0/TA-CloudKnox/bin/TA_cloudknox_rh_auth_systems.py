import ta_cloudknox_declare

import cloudknox_common_utils as utils
from cloudknox_collect import CloudKnoxCollect
import splunk.admin as admin

from solnlib.utils import is_true
from splunktaucclib.rest_handler import util
from log_manager import setup_logging

util.remove_http_proxy_env_vars()

_LOGGER = setup_logging("TA_Cloudknox_auth_systems")


class AuthSystems(admin.MConfigHandler):
    # mapping is created to prevent mal-repsonse injection in DOM
    STATUS_MAPPING = {"ONLINE": "online", "OFFLINE": "offline"}

    def setup(self):
        self.supportedArgs.addOptArg("auth_system_type")

    def handleList(self, conf_info):
        auth_system_type = self.callerArgs.get("auth_system_type")
        if auth_system_type:
            # auth_system_type is in the form of list with one element
            auth_system_type = auth_system_type[0]

            # get cloudknox url, access_key and ssl verification flag from conf
            cloudknox_configs = utils.get_cloudknox_configs()
            ck_url = cloudknox_configs.get("cloudknox_url", "").strip("/")
            ck_account_id = cloudknox_configs.get("account_id", "")
            ck_access_key = cloudknox_configs.get("access_key", "")
            ck_verify_cert = is_true(cloudknox_configs.get("verify_cert", "true"))

            # if any of them are None then the account is not configured
            if not all([ck_url, ck_account_id, ck_access_key]):
                message = "CloudKnox credentials are not configured!"
                _LOGGER.error(message)
                raise admin.ArgValidationException(message)

            # set splunk context vars
            app_name = self.appName
            splunk_session_key = self.getSessionKey()

            # # Initialize CloudKnoxCollect Object
            collect_obj = CloudKnoxCollect(splunk_session_key, app_name)

            try:
                # # # Get all authsystems using CloudKnoxCollect Object
                response = collect_obj.cloudknox_get_all_auth_systems()
                _LOGGER.info("Fetching CloudKnox auth systems.")
                # try to load the response as json
                auth_systems = response.json().get("data")
            except Exception as e:
                _LOGGER.error("Unexpected error occurred: {}".format(e))
                raise e

            else:
                # add "All" option
                conf_info["All"]
                for auth_system in auth_systems:
                    if auth_system["type"] == auth_system_type:
                        offline_status = "[OFFLINE] " if self.STATUS_MAPPING.get(auth_system["status"], "invalid") == "offline" else ""
                        conf_info[offline_status + auth_system["name"] + " (" + auth_system["id"] + ")"].append(
                            "id", auth_system["id"]
                        )
                        conf_info[offline_status + auth_system["name"] + " (" + auth_system["id"] + ")"].append(
                            "status", self.STATUS_MAPPING.get(auth_system["status"], "invalid"),
                        )


if __name__ == "__main__":
    admin.init(AuthSystems, admin.CONTEXT_NONE)

