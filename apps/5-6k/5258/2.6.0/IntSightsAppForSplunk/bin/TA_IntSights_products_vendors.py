import ta_intsights_declare     # noqa: F401
import splunk.admin as admin

from splunktaucclib.rest_handler import util

util.remove_http_proxy_env_vars()
from intsights_utils import get_credentials, get_proxy_info, build_url
import uuid
from base64 import b64encode
import requests
import json
import os
from log_manager import setup_logging
import constants as const

logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0])


class ProductsVendors(admin.MConfigHandler):
    """Get the Products and Vendors list."""

    def setup(self):
        """To setup the variables to access in list."""
        pass

    def handleList(self, conf_info):
        """Populate the Products and Vendors list."""
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
        api_url = "/public/v1/apps/splunk/cves/get-vendor-list"
        try:
            proxies = get_proxy_info(splunk_session_key)
            url = build_url(server_address, api_url)
            response = requests.get(url, verify=verify_cert, headers=header, proxies=proxies, params=payload)
            if response.status_code != 200 and response.status_code != 201:
                raise Exception(
                    "Not able to get list of Products & Vendors. Response Code : {} - "
                    "Response Error : {}".format(response.status_code, response.text)
                )
        except Exception as e:
            message = "Unexpected Error : {}".format(e)
            logger.error(message)
            raise Exception(message)
        else:
            prod_vend_list = (json.loads(response.content)).get('content')
            for each in prod_vend_list:
                conf_info[each].append("id", each)


if __name__ == "__main__":
    """Driving function."""
    admin.init(ProductsVendors, admin.CONTEXT_NONE)
