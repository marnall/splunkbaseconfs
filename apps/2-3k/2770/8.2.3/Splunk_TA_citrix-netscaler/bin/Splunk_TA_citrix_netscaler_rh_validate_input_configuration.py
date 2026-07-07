#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
"""
This module will be used to validate the if the input configuration is valid or not
"""
import import_declare_test  # noqa: F401
import splunk.admin as admin
from solnlib import log, splunkenv
from ta_util2 import utils

log.Logs.set_context()
logger = log.Logs().get_logger("ta_citrix_netscaler_data_duplication")
"""
REST Endpoint to validate the if the input configuration is valid or not
"""


class Splunk_TA_citrix_netscaler_rh_validate_input_configuration(admin.MConfigHandler):
    def setup(self):
        """
        This method checks which action is getting called and what parameters are required for the request.
        """
        if self.requestedAction == admin.ACTION_LIST:
            # Add required args in supported args
            for arg in ("appliances", "templates", "input_name"):
                self.supportedArgs.addReqArg(arg)
        return

    def handleList(self, confInfo):
        """
        This handler is to validate the if the input configuration is valid or not
        It takes  ("appliances", "templates", "input_name") as caller args and
        Returns the confInfo dict object in response.
        """
        logger.info("Entering handler to check input configuration")

        # Get args parameters from the request
        templates = self.callerArgs.data["templates"][0]
        appliances = self.callerArgs.data["appliances"][0]
        input_name = "citrix_netscaler://" + self.callerArgs.data["input_name"][0]

        is_warning = self.check_duplication(input_name, appliances, templates)

        if is_warning:
            confInfo["input_name"]["isValid"] = False
        else:
            confInfo["input_name"]["isValid"] = True

        logger.info("Exiting handler to check input configuration")

    def check_duplication(self, input_name, appliances, templates):
        """
        This method finds the duplicate api endpoints for the input being saved from add-on UI
        """
        input_objs_dict = splunkenv.get_conf_stanzas("inputs")
        appliance_objs_dict = splunkenv.get_conf_stanzas("citrix_netscaler_servers")
        template_objs_dict = splunkenv.get_conf_stanzas("citrix_netscaler_templates")

        is_warning = False
        existing_endpoints = {}

        for task_input in input_objs_dict:
            if (
                ("citrix_netscaler://" not in task_input)
                or task_input == input_name
                or utils.is_true(
                    input_objs_dict.get(task_input, {}).get("disabled", "1")
                )
            ):
                continue
            for task_appliance in (
                input_objs_dict.get(task_input, {}).get("servers", "").split("|")
            ):
                for task_template in (
                    input_objs_dict.get(task_input, {}).get("templates", "").split("|")
                ):
                    for endpoint in (
                        template_objs_dict.get(task_template, {})
                        .get("content", "")
                        .split(";")
                    ):
                        api_endpoint = (
                            appliance_objs_dict.get(task_appliance, {}).get(
                                "server_url", ""
                            )
                            + "``"
                            + endpoint
                        )
                        if api_endpoint not in existing_endpoints:
                            existing_endpoints[api_endpoint] = (
                                endpoint,
                                task_appliance,
                                task_template,
                                task_input,
                            )

        for appliance in appliances.split("|"):
            for template in templates.split("|"):
                unique_endpoint = False
                for endpoint in (
                    template_objs_dict.get(template, {}).get("content", "").split(";")
                ):
                    api_endpoint = (
                        appliance_objs_dict.get(appliance, {}).get("server_url", "")
                        + "``"
                        + endpoint
                    )
                    if api_endpoint not in existing_endpoints:
                        existing_endpoints[api_endpoint] = (
                            endpoint,
                            appliance,
                            template,
                            input_name,
                        )
                        unique_endpoint = True
                    else:
                        logger.warn(
                            "While saving input [ task=({}), "
                            "template=({}), appliance url=({}) ] "
                            "from add-on UI, found duplicate endpoint=({}) "
                            "configuraiton with [ task=({}), template=({}), appliance_url=({}) ],"
                            "which may cause data duplication.".format(
                                input_name.replace("citrix_netscaler://", ""),
                                template,
                                appliance_objs_dict.get(appliance, {}).get(
                                    "server_url", ""
                                ),
                                endpoint,
                                existing_endpoints[api_endpoint][3].replace(
                                    "citrix_netscaler://", ""
                                ),
                                existing_endpoints[api_endpoint][2],
                                appliance_objs_dict.get(
                                    existing_endpoints[api_endpoint][1], {}
                                ).get("server_url", ""),
                            )
                        )

                        is_warning = True

                if not unique_endpoint:
                    logger.warn(
                        "All api endpoints in [ task=({}) , template=({}), appliance url=({}) ] "
                        "duplicate with other tasks.".format(
                            input_name.replace("citrix_netscaler://", ""),
                            template,
                            appliance_objs_dict.get(appliance, {}).get(
                                "server_url", ""
                            ),
                        )
                    )

        return is_warning


if __name__ == "__main__":
    admin.init(
        Splunk_TA_citrix_netscaler_rh_validate_input_configuration,
        admin.CONTEXT_APP_AND_USER,
    )
