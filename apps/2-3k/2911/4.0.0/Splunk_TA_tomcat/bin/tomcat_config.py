#
# SPDX-FileCopyrightText: 2026 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import os.path as op

import import_declare_test  # isort: split

import tomcat_consts as c
from solnlib import conf_manager
from solnlib.log import Logs
from solnlib.modular_input.modinput import get_modinput_configs_from_stdin

assert import_declare_test, "Module is used to filter the sys.path"


def create_tomcat_config():
    meta_configs, stanza_configs = get_modinput_configs_from_stdin()
    return TomcatConfig(meta_configs, stanza_configs)


class TomcatConfig:
    _LOGGER = Logs().get_logger(c.TOMCAT_LOG)
    APP_NAME = "Splunk_TA_tomcat"

    URL_USER_PASSWORDS = ((c.JMX_URL, c.USERNAME, c.PASSWORD),)

    def __init__(self, meta_configs, stanza_configs):
        self._meta_configs = meta_configs
        self._stanza_configs = stanza_configs
        self.account_configs = []
        self.stanza_configs = []
        self.log_level = "NOTSET"
        realm = c.CRED_REALM.format(
            app_name=c.APP_NAME, tomcat_conf=c.TOMCAT_SERVER_CONF
        )
        conf_mgr = conf_manager.ConfManager(
            self._meta_configs[c.SESSION_KEY], self.APP_NAME, realm=realm
        )
        try:
            ta_conf_mgr = conf_mgr.get_conf(c.TOMCAT_SERVER_CONF)
        except conf_manager.ConfManagerException:
            self._LOGGER.info("The Tomcat account hasn't been configured. Exiting.")
            return

        log_settings_mgr = conf_mgr.get_conf(c.TOMCAT_SETTINGS_CONF)
        self.log_level = log_settings_mgr.get(c.LOG_STANZA).get(c.LOG_LEVEL, "INFO")
        ta_conf_mgr.reload()

        for stanza in self._stanza_configs:
            # * Check if the Input contains account field or not.
            # * If not, log an error.
            if not stanza.get("account"):
                self._LOGGER.error(
                    "Tomcat account not found for the input : {}. Please configure the Account "
                    "first. Skipping data collection for this Input.".format(
                        stanza.get("name")
                    )
                )
                continue

            all_account_configs = ta_conf_mgr.get_all()
            account_config = all_account_configs.get(stanza.get("account"))
            if account_config is None:
                self._LOGGER.error(
                    "The account '{}' does not exist. Skipping data collection for '{}' "
                    "input.".format(stanza.get("account"), stanza.get("name"))
                )
                continue
            account_config[c.NAME] = stanza.get("account")

            # * Check if all the required fields are available in the
            # * (splunk_ta_tomcat_account.)conf file. Show the error log even
            # * if one field is not present. Fetch the clear password from
            # * passwords.conf for valid configurations
            if all(account_config.get(k) for k in self.URL_USER_PASSWORDS[0]):
                stanza_to_update = {}
                for field in self.URL_USER_PASSWORDS[0]:
                    stanza_to_update[field] = account_config.get(field)
                ta_conf_mgr.update(
                    stanza.get("account"), stanza_to_update, [c.PASSWORD]
                )
            else:
                self._LOGGER.error(
                    "Tomcat credentials has not been setup for the account: {}. Please setup "
                    "jmx_url, username and password for the account before trying again. "
                    "Skipping data collection for this Input.".format(
                        account_config.get("name")
                    )
                )
                continue

            # * Validate all the fields in input other than account field.
            # * Log an error even if one field is not configured.
            if any(
                not stanza.get(k)
                for k in (
                    c.OBJECT_NAME,
                    c.OPERATION_NAME,
                    c.PARAMS,
                    c.SIGNATURE,
                    c.SPLIT_ARRAY,
                    c.DURATION,
                )
            ):
                self._LOGGER.error(
                    "Some fields are not configured for the input : {}. Please configure all "
                    "the fields - object_name, operation_name, params, signature, split_array. "
                    "Skipping Data collection for this input.".format(
                        stanza.get("name")
                    )
                )
                continue

            # * Check duration field is an integer. If not log an error and
            # * set the duration field to default value i.e 120.
            try:
                duration_int = int(stanza.get("duration"))
                if not 1 <= duration_int <= 31536000:
                    self._LOGGER.warning(
                        "Got unexpected value '{}' of 'duration' field for input '{}'. Duration "
                        "should be an integer. Setting the default value(120). You can either "
                        "change it in inputs.conf file or edit 'Interval' on Inputs page.".format(
                            stanza.get("duration"), stanza.get("name")
                        )
                    )
                    stanza["duration"] = "120"
            except ValueError:
                self._LOGGER.warning(
                    "Got unexpected value '{}' of 'duration' field for input '{}'. Duration "
                    "should be an integer. Setting the default value(120). You can either "
                    "change it in inputs.conf file or edit 'Interval' on Inputs page.".format(
                        stanza.get("duration"), stanza.get("name")
                    )
                )
                stanza["duration"] = "120"

            self.stanza_configs.append(stanza)
            self.account_configs.append(account_config)

    def get_configs(self):
        return (
            self._meta_configs,
            self.stanza_configs,
            self.account_configs,
            self.log_level,
        )
