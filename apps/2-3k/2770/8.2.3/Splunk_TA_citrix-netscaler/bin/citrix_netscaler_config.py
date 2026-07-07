#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import copy
import logging
import os.path as op

from ta_conf import ta_conf_task as tct
from ta_util2 import configure as conf

_LOGGER = logging.getLogger("ta_citrix_netscaler")


class CitrixNetscalerConfig:

    app_dir = op.dirname(op.dirname(op.abspath(__file__)))
    app_file = op.join(app_dir, "local", "app.conf")
    server_file = "citrix_netscaler_servers.conf"
    server_file_w_path = op.join(app_dir, "local", server_file)
    task_file = "inputs.conf"
    task_file_w_path = op.join(app_dir, "local", task_file)
    template_file = "citrix_netscaler_templates.conf"
    template_file_w_path = op.join(app_dir, "local", template_file)
    ucs_file = "splunk_ta_citrix_netscaler_settings.conf"
    ucs_file_w_path = op.join(app_dir, "local", ucs_file)
    ucs_default_file_w_path = op.join(app_dir, "default", ucs_file)
    signal_file_w_path = op.join(app_dir, "local", ".signal")

    def __init__(self, meta_configs):
        self.metas = meta_configs
        self._conf_task = tct.TAConfTask(
            self.metas,
            self.server_file,
            self.template_file,
            self.task_file,
            self.ucs_file,
        )

    def encrypt_credentials(self):
        self._conf_task.encrypt_credentials()

    def get_tasks(
        self, inputs, ui_input_validator_args=None, ui_input_validator_logger=None
    ):
        """
        Generate filter task for data collection based on endpoints

        :param inputs: (dict object) enabled input stanzas
        :param ui_input_validator_args: (tuple object) ui input arguments
        :param ui_input_validator_logger: (object) logging object
        :return:
        """

        confs = (self.server_file, self.template_file, self.task_file, self.ucs_file)
        _LOGGER.info("Reloading configuration files")
        conf.reload_confs(confs, self.metas["session_key"], self.metas["server_uri"])

        tasks = self._conf_task.get_tasks(inputs)

        is_ui_input_warning = False

        if ui_input_validator_args:
            tasks, ui_task_objs = self._separate_tasks(
                tasks, ui_input_validator_args[0]
            )

        filtered_tasks = []
        # Filtered endpoint based on task, if one task have serveral task
        # templates, and some of them have dup class ids, clean them up to
        # avoid dup data collection
        existing_endpoints = {}
        for task in tasks:

            content = task["content"].strip()
            if not content:
                _LOGGER.warn(
                    "No api_endpoint specified for task={}, ignoring it".format(
                        task["name"].replace("citrix_netscaler://", "")
                    )
                )
                continue
            (
                existing_endpoints,
                api_endpoints,
                is_ui_input_warning,
            ) = self._process_api_endpoints(
                task, content, existing_endpoints, ui_logger=None
            )
            filtered_tasks += self._create_filtered_tasks(task, api_endpoints)

        if ui_input_validator_args:

            for task in ui_task_objs:
                ui_task_content = task["content"].strip()
                if not ui_task_content:
                    _LOGGER.warn(
                        "No api_endpoint specified for task={}, ignore it".format(
                            task["name"].replace("citrix_netscaler://", "")
                        )
                    )
                    continue
                (
                    existing_endpoints,
                    api_endpoints,
                    is_ui_input_warning,
                ) = self._process_api_endpoints(
                    task,
                    ui_task_content,
                    existing_endpoints,
                    ui_logger=ui_input_validator_logger,
                )

            if is_ui_input_warning:
                return True
            else:
                return False

        return filtered_tasks

    def _process_api_endpoints(self, task, content, existing_endpoints, ui_logger=None):
        """
        It will process endpoints of the task template and produce necessary warnings regarding data duplication

        :param task: (dict object) input task object
        :param content: (string) string of endpoints
        :param existing_endpoints: (dict object) map for previously configured endpoints
        :param ui_logger: (object) logging object
        :return:
        """

        api_endpoints = []
        unique_api_endpoints = []
        is_ui_input_warning = False
        for endpoint in content.split(";"):
            endpoint = endpoint.strip()
            if not endpoint:
                continue

            # Creating a map for keeping record of unique api endpoints
            et = task["server_url"] + "``" + endpoint
            if et not in existing_endpoints:
                existing_endpoints[et] = (
                    endpoint,
                    task["server_url"],
                    task["task_template"],
                    task["name"],
                )
                unique_api_endpoints.append(endpoint)
            else:
                if ui_logger:

                    # jscpd:ignore-start
                    ui_logger.warn(
                        "While saving input [ task=({}), "
                        "template=({}), appliance url=({}) ] "
                        "from add-on UI, found duplicate endpoint=({}) "
                        "configuraiton with [ task=({}), template=({}), appliance_url=({}) ],"
                        "which may cause data duplication.".format(
                            task["name"].replace("citrix_netscaler://", ""),
                            task["task_template"].replace(
                                self.metas["app_name"] + ":", ""
                            ),
                            task["server_url"],
                            endpoint,
                            existing_endpoints[et][3].replace(
                                "citrix_netscaler://", ""
                            ),
                            existing_endpoints[et][2].replace(
                                self.metas["app_name"] + ":", ""
                            ),
                            existing_endpoints[et][1],
                        )
                    )
                    is_ui_input_warning = True
                else:
                    _LOGGER.warn(
                        "While filtering [ task=({}), template=({}), appliance url=({}) ] found "
                        "api_endpoint=({}) already specified in "
                        "[ task=({}), template=({}), appliance url=({}) will have data duplication."
                        "".format(
                            task["name"].replace("citrix_netscaler://", ""),
                            task["task_template"].replace(
                                self.metas["app_name"] + ":", ""
                            ),
                            task["server_url"],
                            endpoint,
                            existing_endpoints[et][3].replace(
                                "citrix_netscaler://", ""
                            ),
                            existing_endpoints[et][2].replace(
                                self.metas["app_name"] + ":", ""
                            ),
                            existing_endpoints[et][1],
                        )
                    )

            api_endpoints.append(endpoint)
            # jscpd:ignore-end
        if ui_logger:
            self._generate_all_duplicate_endpoints_warning(
                task, unique_api_endpoints, ui_logger
            )
        else:
            self._generate_all_duplicate_endpoints_warning(
                task, unique_api_endpoints, _LOGGER
            )

        return existing_endpoints, api_endpoints, is_ui_input_warning

    @staticmethod
    def _separate_tasks(tasks, input_name):
        """
        It will separate tasks in two list
        (tasks matches the input name) & (tasks which does not matches the input name)

        :param tasks: (list) inputs task objects
        :param input_name: (string) name of input
        :return:
        """
        return [task for task in tasks if task["name"] != input_name], [
            task for task in tasks if task["name"] == input_name
        ]

    @staticmethod
    def _create_filtered_tasks(task, api_endpoints):
        """
        It will create filtered objects based on endpoints list

        :param task: (dict object) the input task object
        :param api_endpoints: (list) list of endpoints
        :return:
        """
        filtered_tasks = []
        for endpoint in api_endpoints:
            dup = copy.deepcopy(task)
            dup["url"] = dup["server_url"]
            dup["username"] = dup["account_name"]
            dup["password"] = dup["account_password"]
            dup["duration"] = int(dup["duration"])
            dup["api_endpoint"] = endpoint

            for k in ("server_url", "account_name", "account_password", "content"):
                del dup[k]
            filtered_tasks.append(dup)

        return filtered_tasks

    def _generate_all_duplicate_endpoints_warning(
        self, task, api_endpoints, logger=None
    ):
        """
        It will log warning message
        :param task: (dict object) the input task object
        :param api_endpoints: (list) list of unique endpoints
        :param logger: (object)logging object
        :return:
        """
        if not api_endpoints:
            logger.warn(
                "All api endpoints in [ task=({}) , template=({}), appliance url=({}) ] "
                "duplicate with other tasks.".format(
                    task["name"].replace("citrix_netscaler://", ""),
                    task["task_template"].replace(self.metas["app_name"] + ":", ""),
                    task["server_url"],
                )
            )
