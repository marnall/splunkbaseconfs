#
# SPDX-FileCopyrightText: 2026 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import os.path as op
import import_declare_test

# Switched from splunktalib.credentials to solnlib.credentials (modern Splunk library);
# also imports CredentialNotExistException for safe error handling during password retrieval
from solnlib.credentials import CredentialManager, CredentialNotExistException
from splunktalib.common.log import Logs
from splunktalib.modinput import parse_modinput_configs
from splunktalib.conf_manager.ta_conf_manager import TAConfManager
from splunktalib.modinput import get_modinput_configs_from_stdin
import sys

# urlparse splits SERVER_URI into scheme/host/port, which solnlib.CredentialManager requires as separate args
from urllib.parse import urlparse

import json
import jboss_consts as c


def create_jboss_config():
    meta_configs, stanza_configs = get_modinput_configs_from_stdin()
    return JBossConfig(meta_configs, stanza_configs)


class JBossConfig:
    """
    Loads and validates JBoss modular input configuration at startup.

      Before fix: used splunktalib's get_clear_password() which returned a dict
                  keyed by a CRED_REALM-formatted string — fragile and tightly coupled
                  to internal splunktalib behaviour.
      After fix:  uses solnlib's get_password() which returns a plain JSON string.
                  The password is extracted with json.loads() and validated explicitly.
                  If the credential is missing or malformed, the stanza is skipped with
                  a clear error log instead of crashing the whole modular input.

    Ticket: ADDON-86488
    """

    _LOGGER = Logs().get_logger("main")
    # UCC-standard realm format used to look up credentials stored via the Accounts REST endpoint in passwords.conf
    UCC_CRED_REALM = "__REST_CREDENTIAL__#{app_name}#{endpoint}"
    UCC_ACCOUNT_ENDPOINT = "Splunk_TA_jboss_account"

    URL_USER_PASSWORDS = ((c.JMX_URL, c.USERNAME, c.PASSWORD),)

    def __init__(self, meta_configs, stanza_configs):
        """
        For each input stanza:
          1. Verify the 'account' field is set.
          2. Look up the account in splunk_ta_jboss_account.conf.
          3. Retrieve the password from passwords.conf via solnlib CredentialManager.
          4. Validate all required input fields (object_name, operation_name, etc.).
          5. Validate and normalise the 'duration' field.
        Stanzas that fail any step are skipped with an error log; the rest are
        collected into self.stanza_configs and self.account_configs for the caller.
        """
        self._meta_configs = meta_configs
        self._stanza_configs = stanza_configs
        self.account_configs = []
        self.stanza_configs = []
        ta_conf_mgr = TAConfManager(
            c.JBOSS_SERVER_CONF,
            self._meta_configs[c.SERVER_URI],
            self._meta_configs[c.SESSION_KEY],
        )
        log_settings_mgr = TAConfManager(
            c.JBOSS_SETTINGS_CONF,
            self._meta_configs[c.SERVER_URI],
            self._meta_configs[c.SESSION_KEY],
        )

        # solnlib.CredentialManager requires scheme/host/port separately; urlparse splits the SERVER_URI string
        # Realm follows the UCC __REST_CREDENTIAL__ format so it matches entries written by the Accounts UI
        splunkd_info = urlparse(self._meta_configs[c.SERVER_URI])
        crm = CredentialManager(
            self._meta_configs[c.SESSION_KEY],
            c.MODINPUT_NAME,
            owner="nobody",
            realm=self.UCC_CRED_REALM.format(
                app_name=c.MODINPUT_NAME,
                endpoint=self.UCC_ACCOUNT_ENDPOINT,
            ),
            scheme=splunkd_info.scheme,
            host=splunkd_info.hostname,
            port=splunkd_info.port,
        )
        self.log_level = log_settings_mgr.get(c.LOG_STANZA).get(c.LOG_LEVEL, "INFO")
        ta_conf_mgr.reload()

        for stanza in self._stanza_configs:
            # * Check if the Input contains account field or not. If not, log an error.
            if not stanza.get("account"):
                self._LOGGER.error(
                    "JBoss account not found for the input : {}. Please configure the Account first. Skipping data collection for this Input.".format(
                        stanza.get("name")
                    )
                )
                continue

            all_account_configs = ta_conf_mgr.all()
            account_config = all_account_configs.get(stanza.get("account"))
            if account_config is None:
                self._LOGGER.error(
                    "The account '{}' does not exist. Skipping data collection for '{}' input.".format(
                        stanza.get("account"), stanza.get("name")
                    )
                )
                continue

            # * Check if all the required fields are available in the (splunk_ta_jboss_account.)conf file. Show the error log even if one field is not present. Fetch the clear password from passwords.conf for valid configurations
            if all(account_config.get(k) for k in self.URL_USER_PASSWORDS[0]):
                ta_conf_mgr.set_encrypt_keys([c.PASSWORD])
                if not ta_conf_mgr.is_encrypted(account_config):
                    ta_conf_mgr.update(account_config)
                else:
                    # Replaced get_clear_password() (splunktalib) with get_password() (solnlib);
                    # wrapped in try/except because missing or malformed credentials should skip the stanza gracefully
                    # rather than crashing the entire modular input process
                    try:
                        clear_password = json.loads(
                            crm.get_password(stanza.get("account"))
                        )
                        password = clear_password.get(c.PASSWORD)
                        if not password:
                            raise ValueError("No stored password found")
                        account_config[c.PASSWORD] = password
                    except (
                        CredentialNotExistException,  # credential entry does not exist in passwords.conf
                        ValueError,  # JSON parse failed or password key missing
                        TypeError,  # get_password returned None
                    ) as error:
                        self._LOGGER.error(
                            "Failed to retrieve password for account '{}'. "
                            "Please re-save the account credentials. error={}".format(
                                stanza.get("account"), error
                            )
                        )
                        continue
            else:
                self._LOGGER.error(
                    "JBoss credentials has not been setup for the account : {}. Please setup jmx_url, username and password for the account before trying again. Skipping data collection for this Input.".format(
                        account_config.get("name")
                    )
                )
                continue

            # * Validate all the fields in input other than account field. Log an error even if one field is not configured.
            if any(
                (
                    not stanza.get(k)
                    for k in (
                        c.OBJECT_NAME,
                        c.OPERATION_NAME,
                        c.PARAMS,
                        c.SIGNATURE,
                        c.SPLIT_ARRAY,
                        c.DURATION,
                    )
                )
            ):
                self._LOGGER.error(
                    "Some fields are not configured for the input : {}. Please configure all the fields - object_name, operation_name, params, signature, split_array. Skipping Data collection for this input.".format(
                        stanza.get("name")
                    )
                )
                continue

            # * Check duration field is an integer. If not log an error and set the duration field to default value i.e 120.
            try:
                duration_int = int(stanza.get("duration"))
                if not 1 <= duration_int <= 31536000:
                    self._LOGGER.warning(
                        "Got unexpected value '{}' of 'duration' field for input '{}'. Duration should be an integer. Setting the default value(120)."
                        " You can either change it in inputs.conf file or edit 'Interval' on Inputs page.".format(
                            stanza.get("duration"), stanza.get("name")
                        )
                    )
                    stanza["duration"] = "120"
            except ValueError:
                self._LOGGER.warning(
                    "Got unexpected value '{}' of 'duration' field for input '{}'. Duration should be an integer. Setting the default value(120)."
                    " You can either change it in inputs.conf file or edit 'Interval' on Inputs page.".format(
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
