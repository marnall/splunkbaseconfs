import ta_intsights_declare     # noqa: F401
import splunk.admin as admin

from splunktaucclib.rest_handler import util

util.remove_http_proxy_env_vars()
from intsights_utils import get_credentials
import json
import os
from log_manager import setup_logging
import splunk.rest as rest

logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0])


class ProductsVendorsFilters(admin.MConfigHandler):
    """Get the Products and Vendors Filters list."""

    def setup(self):
        """To setup the variables to access Filters."""
        pass

    def handleList(self, conf_info):
        """Populate the Products and Vendors Filters."""
        # set splunk context vars
        splunk_session_key = self.getSessionKey()
        account_details = get_credentials("account", splunk_session_key)
        api_key = account_details.get("api_key", "")
        account_id = account_details.get("account_id", "")
        server_address = account_details.get("server_address", "")
        if not all([api_key, account_id, server_address]):
            message = "IntSights account is not configured!"
            logger.error("IntSights account is not configured.")
            raise ValueError(message)
        try:
            resp, content = rest.simpleRequest(
                "/servicesNS/nobody/{}/configs/conf-ta_intsights_products_vendors_filters".format(
                    ta_intsights_declare.ta_name
                ),
                sessionKey=splunk_session_key,
                getargs={"output_mode": "json"},
            )
            content = json.loads(content)
        except Exception as e:
            message = "Unexpected Error : {}".format(e)
            logger.error(message)
            raise Exception(message)
        else:
            conf_info["All"]
            for each in content['entry']:
                conf_info[each['name']].append("id", each['name'])


if __name__ == "__main__":
    """Driving function."""
    admin.init(ProductsVendorsFilters, admin.CONTEXT_NONE)
