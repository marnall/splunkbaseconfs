import ta_intsights_declare     # noqa: F401
import splunk.admin as admin

from splunktaucclib.rest_handler import util

util.remove_http_proxy_env_vars()
from intsights_utils import get_credentials, get_proxy_info, build_url
import uuid
from base64 import b64encode
import requests
import json
import traceback
import os
from log_manager import setup_logging
import constants as const

logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0])


class ReportingFeeds(admin.MConfigHandler):
    """Get the Reporting feeds data."""

    def setup(self):
        """To setup the variables to access in list."""
        pass

    def handleList(self, conf_info):
        """Populate the reporting feeds."""
        # set splunk context vars
        splunk_session_key = self.getSessionKey()
        account_details = get_credentials("account", splunk_session_key)
        api_key = account_details.get("api_key", "")
        account_id = account_details.get("account_id", "")
        server_address = account_details.get("server_address", "")
        verify_cert = const.VERIFY_SSL
        if not all([api_key, account_id, server_address]):
            message = "IntSights account is not configured!"
            logger.error("IntSights account is not configured.")
            raise ValueError(message)
        encoded_cred = b64encode("{}:{}".format(account_id,
                                                api_key).encode()).decode()
        header = {
            "Content-type": "application/json",
            "Accept": "application/json",
            "Authorization": "Basic {}".format(encoded_cred)
        }
        sync_id = str(uuid.uuid4())
        payload = {'syncId': sync_id}
        api_url = "/public/v1/apps/splunk/iocs/sources"
        try:
            proxies = get_proxy_info(splunk_session_key)
            url = build_url(server_address, api_url)
            response = requests.get(url, verify=verify_cert, headers=header, proxies=proxies, params=payload)
            if response.status_code != 200 and response.status_code != 201:
                raise Exception(
                    "Not able to get list of reporting feeds . Response Code : {}"
                    "- Response Error : {}".format(response.status_code, response.text)
                )
        except Exception as e:
            message = "Unexpected Error : {}".format(e)
            logger.error("{} \n Traceback : {}".format(message, traceback.format_exc()))
            raise Exception(message)
        else:
            # add "All" option
            conf_info["All"]
            sources_data = (json.loads(response.content)).get('content')
            for sources in sources_data.keys():
                for source in sources_data.get(sources):
                    if source.get("IsEnabled"):
                        conf_info[source["Name"]].append("id", source["_id"])


if __name__ == "__main__":
    """Driving function."""
    admin.init(ReportingFeeds, admin.CONTEXT_NONE)
