#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This file is the custom rest handler file for the input validation.

This file contains certain ignores for certain linters.
* isort ignores:
- isort: skip = Should not be sorted.
* flake8 ignores:
- noqa: E401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import import_declare_test  # isort: skip # noqa: F401
import splunk.admin as admin
from solnlib import log
from splunk_ta_ms_scom_util import get_all_in_use_managementgroups

log.Logs.set_context()
_LOGGER = log.Logs().get_logger("splunk_ta_microsoft-scom_input_validation")


class InputDataDuplicationValidationHandler(admin.MConfigHandler):
    """
    REST Endpoint to validate data duplication occurs or not
    """

    def setup(self):
        """
        This method checks which action is getting called and what parameters are required for the request.
        :return: None
        """
        if self.requestedAction == admin.ACTION_LIST:
            # Add required args in supported args
            for arg in ("templates", "server", "input_name"):
                self.supportedArgs.addReqArg(arg)

    def handleList(self, conf_info):
        """
        This handler is to validate the if the input configuration is valid or not
        It takes  ("server", "templates", "input_name") as caller args and
         Returns the confInfo dict object in response.
        :param conf_info: response dict
        :return: None
        """
        # Get args parameters from the request
        templates_for_current_input = self.callerArgs.data.get("templates")[0].split(
            "|"
        )
        server_for_current_input = self.callerArgs.data.get("server")[0]
        input_name = self.callerArgs.data.get("input_name")[0]

        conf_info[input_name]["duplicate_warning"] = self.check_data_duplication_loss(
            server_for_current_input, templates_for_current_input, input_name
        )

    def check_data_duplication_loss(
        self, server_for_current_input, templates_for_current_input, input_name
    ):
        """
        This method is to validate that if the input could cause data duplication/loss.
        It takes  ("server_for_current_input", "templates_for_current_input") as
        server and templates for current input and returns-
        - True: If there is/are any input(s) with same combination of server and template
        - False: If not.
        """
        servers_and_templates = get_all_in_use_managementgroups(
            self.getSessionKey(), self.userName, self.appName, get_both=True
        )

        server_is_same = False
        templates_are_same = False
        same_serv_templ_comb = None

        for server_and_template in servers_and_templates:

            if server_for_current_input != server_and_template.get("server"):
                continue
            else:
                server_is_same = True

            for template in templates_for_current_input:
                if template in server_and_template.get("templates"):
                    templates_are_same = True
                    break

            if server_is_same and templates_are_same:
                same_serv_templ_comb = server_and_template.get("name")
                break

        if server_is_same and templates_are_same:
            _LOGGER.warning(
                "While configuring input '{}', selected server and one or more of the selected "
                "templates are same as the input: '{}'. To avoid data duplication/loss, "
                "please select a new server and try again.".format(
                    input_name, same_serv_templ_comb
                )
            )
            return True
        return False


if __name__ == "__main__":
    admin.init(InputDataDuplicationValidationHandler, admin.CONTEXT_APP_AND_USER)
