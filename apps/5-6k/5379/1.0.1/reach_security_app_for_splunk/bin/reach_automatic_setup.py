# Standard library imports
import os
import sys
import json
import csv
import splunk.rest as rest

sys.path.insert(0, os.path.sep.join([os.path.dirname(__file__)]))

# Local imports
import reach_security_app_for_splunk_declare
import reach_search_execution_helper
import reach_logger_manager as log


class AutomaticSetup(rest.BaseRestHandler):
    """Class for getting UI validation message through custom endpoint."""

    def save_default_configs(self, products):
        """
        Save the configured products
        :param products: available products in Splunk
        """
        try:
            rest.simpleRequest(
                "/servicesNS/nobody/reach_security_app_for_splunk/reach_security_app_for_splunk_settings/additional_parameters?output_mode=json",
                self.sessionKey,
                postargs={"products" : str(",".join(products))},
                method="POST",
                raiseAllErrors=True,
            )
        except Exception as err:
            err = "Error Occured while updating settings in conf file. Please setup manually."
            raise Exception(err)

    def handle_POST(self):
        """Handle POST requests from frontend."""
        try:
            logger = log.setup_logging('reach_setup', self.sessionKey)
            products, status = reach_search_execution_helper.update_configured_macro(self.sessionKey, logger, configured_products="")
            self.save_default_configs(products)
        except Exception as err:
            raise Exception(err)
        finally:
            self.response.setHeader('content-type', 'application/json')
            response = json.dumps(
                '{"message":"Successfully Configured App. You can execute the search by visiting Export dashboard."}')
            self.response.write(response)

    # handle verbs, otherwise Splunk will throw an error
    handle_GET = handle_POST
