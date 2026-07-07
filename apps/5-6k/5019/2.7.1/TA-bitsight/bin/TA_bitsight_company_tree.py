import import_declare_test     # noqa: F401

import json
import traceback
import os

import splunk.admin as admin
from splunktaucclib.rest_handler import util

from bitsight_utils import BitsightCompanyGuidMapper
from setup_logger import setup_logging
from bitsight_exceptions import BitsightException

util.remove_http_proxy_env_vars()

logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0].lower())


class CompanyTree(admin.MConfigHandler):
    """Get the Reporting feeds data."""

    def setup(self):
        """To setup the variables to access in list."""
        pass

    def handleList(self, conf_info):
        """Populate the company multiselect dropdown."""
        # set splunk context vars
        splunk_session_key = self.getSessionKey()
        bsobject = BitsightCompanyGuidMapper(splunk_session_key, "spm")
        try:
            response = bsobject.get_company_tree()
            if not response:
                msg = "Unable to request BitSight instance. "\
                      "Please validate the provided BitSight and "\
                      "Proxy configurations or check the network connectivity."
                raise BitsightException(msg)
            if response.status_code != 200 and response.status_code != 201:
                raise BitsightException(
                    "Not able to get list of subsidiary companies . Response Code : {}"
                    "- Response Error : {}".format(response.status_code, response.text)
                )
        except TypeError:
            message = "Please configure the BitSight API URL and/or BitSight API Token before creating input."
            logger.error(message)
        except Exception as e:
            message = "Unexpected Error : {}".format(e)
            logger.error("{} \n Traceback : {}".format(message, traceback.format_exc()))
            raise BitsightException(message)
        else:
            # add "All" option
            conf_info["All"]
            comp_data = (json.loads(response.content)).get('results')
            logger.debug("Got {} subsidiaries.".format(len(comp_data)))
            for each in comp_data:
                conf_info[each['name']]


if __name__ == "__main__":
    """Driving function."""
    admin.init(CompanyTree, admin.CONTEXT_NONE)
