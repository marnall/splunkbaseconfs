#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
"""
This script migrates the tasks stored in cisco_ucs_tasks.conf in the TA version less than 4.0.0 into the inputs.conf.
"""

import logging
import json
import traceback


import import_declare_test
import splunk_ta_cisco_ucs_constants as constants
import splunk.rest as rest
from splunklib import binding
from solnlib import conf_manager, log
import splunk_ta_cisco_ucs_migration_utility as utility

logger = logging.getLogger(constants.TA_NAME.lower() + "_migration")


class MigrateExistingInputs:
    """
    This class is used to migrate the existing tasks to inputs.conf file.
    """

    def get_tasks(self, session_key):
        """
        This function is used to get the tasks that are configured in the existing addon.
        :param session_key: The session key value.
        :return tasks_obj: The function returns the list of tasks that are configured in the existing addon.
        """
        try:
            response_code, repsonse_content = rest.simpleRequest(
                "/servicesNS/nobody/-/configs/conf-cisco_ucs_tasks",
                sessionKey=session_key,
                getargs={"output_mode": "json", "count": "0"},
            )
            json_content = json.loads(repsonse_content)
            tasks_obj = json_content.get("entry")
            return tasks_obj
        except Exception as e:
            log.log_exception(
                logger, e, "Error while getting tasks from cisco_ucs_tasks.conf file"
            )

    def transfer_data_to_inputs(self, session_key, tasks_list):
        """
        This function is used to transfer the stanzas from the cisco_ucs_tasks.conf file to inputs.conf file.
        :param session_key: The session key value.
        :param tasks_list: The list of the tasks that are configured in the existing addon.
        """

        try:
            cfm = conf_manager.ConfManager(session_key, constants.TA_NAME)
            cfm_input = cfm.get_conf(constants.INPUTS_CONF_FILE)
            for task in tasks_list:
                new_dict = {}
                task_content = task.get("content")
                stanza_name = "".join(["cisco_ucs_task://", task["name"]])
                if task_content.get("description"):
                    new_dict["description"] = task_content["description"]
                if task_content.get("disabled"):
                    new_dict["disabled"] = task_content["disabled"]
                if "index" in task_content and task_content["index"] != "default":
                    new_dict["index"] = task_content["index"]
                if task_content.get("interval"):
                    new_dict["interval"] = task_content["interval"]
                if task_content.get("sourcetype"):
                    new_dict["sourcetype"] = task_content["sourcetype"]
                if task_content.get("servers"):
                    new_dict["servers"] = self.form_new_value(task_content["servers"])
                if task_content.get("templates"):
                    new_dict["templates"] = self.form_new_value(
                        task_content["templates"]
                    )
                cfm_input.update(stanza_name, new_dict)

        except binding.HTTPError as e:
            log.log_exception(logger, e, "HTTPError")
        except KeyError as e:
            log.log_exception(logger, e, "KeyError")
        except Exception:
            log.log_exception(logger, e, "exception raised")

    def transfer_existing_inputs(self):
        """
        This function is used to perform all the operations required to transfer the existing tasks to inputs.conf file.
        """
        try:
            logger.debug("Proceeding to migrate existing tasks into inputs.conf")
            dict_inputs_transfer = {}
            has_migrated = "0"
            session_key = utility.get_session_key()
            cfm = conf_manager.ConfManager(session_key, constants.TA_NAME)
            settings_file_exists = utility.file_exist(
                constants.SETTINGS_CONF_FILE, constants.TA_NAME
            )
            if not settings_file_exists:
                logger.info(
                    "settings conf does not exist. Proceeding to create settings conf."
                )
                utility.create_splunk_ta_cisco_ucs_settings_conf_file(
                    cfm, constants.INPUTS_MIGRATION_STANZA, session_key
                )
            else:
                has_migrated = utility.check_has_migrated_value(
                    cfm, constants.INPUTS_MIGRATION_STANZA
                )
            if has_migrated == "0":
                tasks_list = self.get_tasks(session_key)
                self.transfer_data_to_inputs(session_key, tasks_list)
                utility.update_settings_conf(
                    session_key, constants.INPUTS_MIGRATION_STANZA
                )
                logger.info("Tasks migration has been completed.")
        except Exception as e:
            log.log_exception(logger, e, "Error while migrating tasks")

    def form_new_value(self, value):
        """
        This function is used to remove the destination app value from the servers and templates value in the cisco_ucs_tasks.conf file.
        :param value: The function takes the value of the server or template from which the destination app value needs to be removed.
        :return: This function returns the new value formed after removing destination app value from the servers and templates value.
        """

        old_list = value.split(" | ")
        new_list = [server.split(":")[1] for server in old_list]

        return "|".join(new_list)


if __name__ == "__main__":
    migrate_inputs = MigrateExistingInputs()
    migrate_inputs.transfer_existing_inputs()
