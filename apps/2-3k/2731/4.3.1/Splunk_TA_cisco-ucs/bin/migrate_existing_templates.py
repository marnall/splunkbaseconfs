#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
"""
This script migrates the templates stored in cisco_ucs_templates.conf in the TA version less than 4.0.0 into the splunk_ta_cisco_ucs_templates.conf.
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


class MigrateExistingTemplates:
    """
    This class is used to migrate the existing templates to splunk_ta_cisco_ucs_templates.conf file.
    """

    def get_templates(self, session_key):
        """
        This function is used to get the templates that are configured in the existing addon.
        :param session_key: The session key value.
        :return templates_obj: The function returns the list of templates that are configured in the existing addon.
        """
        try:
            response_code, repsonse_content = rest.simpleRequest(
                "/servicesNS/nobody/-/configs/conf-cisco_ucs_templates",
                sessionKey=session_key,
                getargs={"output_mode": "json", "count": "0"},
            )
            json_content = json.loads(repsonse_content)
            templates_obj = json_content.get("entry")
            return templates_obj
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "Error while getting templates from cisco_ucs_templates.conf file.",
            )

    def transfer_data_to_new_templates_conf(self, session_key, templates_list):
        """
        This function is used to transfer the stanzas from the cisco_ucs_templates.conf file to templates.conf file.
        :param session_key: The session key value.
        :param templates_list: The list of the templates that are configured in the existing addon.
        """

        try:
            cfm = conf_manager.ConfManager(session_key, constants.TA_NAME)
            new_templates_file_exists = utility.file_exist(
                constants.TEMPLATES_CONF, constants.TA_NAME
            )
            if not new_templates_file_exists:
                cfm.create_conf(constants.TEMPLATES_CONF)
            cfm_input = cfm.get_conf(constants.TEMPLATES_CONF)
            for template in templates_list:
                new_dict = {}
                template_content = template.get("content")
                stanza_name = template["name"]
                if template_content.get("description"):
                    new_dict["description"] = template_content["description"]
                if template_content.get("content"):
                    new_dict["content"] = template_content["content"]
                cfm_input.update(stanza_name, new_dict)

        except binding.HTTPError as e:
            log.log_exception(logger, e, "HTTPError")
        except KeyError as e:
            log.log_exception(logger, e, "Keyerror exception")
        except Exception as e:
            log.log_exception(logger, e, "exception raised")

    def transfer_existing_templates(self):
        """
        This function is used to perform all the operations required to transfer the existing templates to splunk_ta_cisco_ucs_templates.conf file.
        """
        try:
            logger.debug(
                "Proceeding to migrate existing templates into {}.conf".format(
                    constants.TEMPLATES_CONF
                )
            )
            dict_templates_transfer = {}
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
                    cfm, constants.TEMPLATES_MIGRATION_STANZA, session_key
                )
            else:
                has_migrated = utility.check_has_migrated_value(
                    cfm, constants.TEMPLATES_MIGRATION_STANZA
                )
            if has_migrated == "0":
                templates_list = self.get_templates(session_key)
                self.transfer_data_to_new_templates_conf(session_key, templates_list)
                utility.update_settings_conf(
                    session_key, constants.TEMPLATES_MIGRATION_STANZA
                )
                logger.info(
                    "Templates migration has been completed. All templates are now stored in local/{}.conf".format(
                        constants.TEMPLATES_CONF
                    )
                )
        except Exception as e:
            log.log_exception(logger, e, "Error while migrating templates.")


if __name__ == "__main__":
    migrate_templates = MigrateExistingTemplates()
    migrate_templates.transfer_existing_templates()
