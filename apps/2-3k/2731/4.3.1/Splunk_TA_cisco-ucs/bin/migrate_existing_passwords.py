#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
"""
This script migrates the passwords stored in cisco_ucs_servers.conf in the TA version less than 4.0.0 to a new format according to the UCC 5.x standards.
"""

import logging
import json
import traceback

import import_declare_test
import splunk_ta_cisco_ucs_constants as constants
import splunk_ta_cisco_ucs_migration_utility as utility
import splunk.entity as entity
import splunk.rest as rest
from solnlib import conf_manager, log

logger = logging.getLogger(constants.TA_NAME.lower() + "_migration")


class MigrateExistingPasswords:
    """
    This class is used to migrate the existing passwords to the new format.
    """

    def update_server_conf(self, session_key, creds_list):
        """
        This function is used to update the cisco_ucs_servers.conf file.
        :param session_key: The session_key value.
        :param creds_list: The list of existing credentials.
        """

        try:
            cfm = conf_manager.ConfManager(
                session_key,
                constants.TA_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                    constants.TA_NAME, constants.SERVERS_CONF
                ),
            )
            servers_conf_exist = utility.file_exist(
                constants.SERVERS_CONF, constants.TA_NAME
            )
            if not servers_conf_exist:
                cfm.create_conf(constants.SERVERS_CONF)
            servers_conf_obj = cfm.get_conf(constants.SERVERS_CONF)
            for value in creds_list:
                server_details = {
                    key: val for key, val in value.items() if key != "name"
                }
                server_name = value["name"]
                servers_conf_obj.update(
                    server_name, server_details, ["account_password"]
                )

        except Exception as e:
            log.log_exception(
                logger, e, "Exception occured while getting servers_conf object."
            )

    def get_credentials(self, session_key):
        """
        :param session_key: The session_key value.
        :return creds_list: Returns the list of the existing credentials
        """

        # make a call for all entries in all cisco_ucs_servers.conf

        try:
            logger.info(
                "Proceeding to get the server details from all cisco_ucs_servers.conf"
            )
            creds_list = []
            _, response_content = rest.simpleRequest(
                "/servicesNS/nobody/-/configs/conf-cisco_ucs_servers",
                sessionKey=session_key,
                getargs={"output_mode": "json"},
            )
            json_obj = json.loads(response_content).get("entry")

            for each_server in json_obj:
                creds_dict = {}
                server_name = each_server["name"]
                creds_dict["name"] = server_name
                if each_server.get("content"):
                    content = each_server["content"]
                    if content.get("description"):
                        creds_dict["description"] = content["description"]
                    if content.get("server_url"):
                        creds_dict["server_url"] = content["server_url"]
                    if content.get("disable_ssl_verification"):
                        creds_dict["disable_ssl_verification"] = content[
                            "disable_ssl_verification"
                        ]
                    if (
                        content.get("account_name") == "******"
                        and content.get("account_password") == "******"
                    ):
                        search_string = (
                            "_"
                            + content["eai:appName"]
                            + "_account_#"
                            + content["eai:appName"]
                            + "#"
                            + server_name
                        )

                        entities = entity.getEntities(
                            ["admin", "passwords"],
                            namespace=constants.TA_NAME,
                            owner="nobody",
                            sessionKey=session_key,
                            count=-1,
                            search=search_string,
                        )

                        for stanza, value in entities.items():
                            if "clear_password" in value:
                                clear_password_splitted = value["clear_password"].split(
                                    "``"
                                )
                                creds_dict["account_name"] = clear_password_splitted[0]
                                creds_dict[
                                    "account_password"
                                ] = clear_password_splitted[1]
                    else:
                        logger.debug(
                            'credentials were not encrypted for the server "{}" in the app {}'.format(
                                server_name, content["eai:appName"]
                            )
                        )
                        creds_dict["account_name"] = content.get("account_name")
                        creds_dict["account_password"] = content.get("account_password")
                creds_list.append(creds_dict)

        except Exception as e:
            log.log_exception(
                logger,
                e,
                "error while retrieveing server details from the cisco_ucs_servers.conf.",
            )

        return creds_list

    def migrate_existing_passwords(self):
        """
        This function is used to migrate the existing passwords to the new format.
        """
        try:
            has_migrated = "0"
            session_key = utility.get_session_key()
            cfm = conf_manager.ConfManager(session_key, constants.TA_NAME)
            setting_conf_exist = utility.file_exist(
                constants.SETTINGS_CONF_FILE, constants.TA_NAME
            )
            if not setting_conf_exist:
                utility.create_splunk_ta_cisco_ucs_settings_conf_file(
                    cfm, constants.PASSWORDS_MIGRATION_STANZA, session_key
                )
            else:
                has_migrated = utility.check_has_migrated_value(
                    cfm, constants.PASSWORDS_MIGRATION_STANZA
                )

            if has_migrated == "0":
                logger.debug(
                    "Passwords have not been migrated yet. Proceeding to migrate passwords."
                )
                creds = self.get_credentials(session_key)
                self.update_server_conf(session_key, creds)
                utility.update_settings_conf(
                    session_key, constants.PASSWORDS_MIGRATION_STANZA
                )
                logger.info(
                    "Passwords migration has been completed. Servers are now stored in local/{}.conf".format(
                        constants.SERVERS_CONF
                    )
                )
        except Exception as e:
            log.log_exception(logger, e, "Error while migrating passwords.")


if __name__ == "__main__":
    migrate_passwords = MigrateExistingPasswords()
    migrate_passwords.migrate_existing_passwords()
