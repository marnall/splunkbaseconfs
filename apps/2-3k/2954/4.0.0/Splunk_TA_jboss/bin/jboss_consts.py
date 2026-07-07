#
# SPDX-FileCopyrightText: 2026 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import os

# Global
APP_NAME = "jboss"
SESSION_KEY = "session_key"
SERVER_URI = "server_uri"
CHECKPOINT_DIR = "checkpoint_dir"
STATE_STORE = "state_store"
HOST = "host"
NAME = "name"
CRED_REALM = "__REST_CREDENTIAL__#Splunk_TA_{app_name}#configs/conf-{jboss_conf}"

SPLUNK_HOME = os.environ["SPLUNK_HOME"]
MODINPUT_NAME = "Splunk_TA_jboss"
MODINPUT_HOME = os.path.sep.join([SPLUNK_HOME, "etc", "apps", MODINPUT_NAME])

# Conf files
JBOSS_LOG = "main"
INPUT_VALIDATION_LOG_FILE = "account_validation"
JBOSS_SETTINGS_CONF_FILE = "splunk_ta_jboss_settings.conf"
JBOSS_SETTINGS_CONF = "splunk_ta_jboss_settings"
JBOSS_SERVER_CONF_FILE = "splunk_ta_jboss_account.conf"
JBOSS_SERVER_CONF = "splunk_ta_jboss_account"
INPUTS_CONF = "inputs"

# JBoss Server Stanzas
JMX_URL = "jmx_url"
USERNAME = "username"
PASSWORD = "password"
INDEX = "index"

# Log settings
LOG_STANZA = "logging"
LOG_LEVEL = "loglevel"

NAME = "name"
OBJECT_NAME = "object_name"
OPERATION_NAME = "operation_name"
PARAMS = "params"
SIGNATURE = "signature"
SPLIT_ARRAY = "split_array"
DURATION = "duration"
SOURCETYPE = "sourcetype"

# Other
LOG_PATH_PARAMS = "-Dlog.path="
LOG_PATH = os.path.sep.join(
    [SPLUNK_HOME, "var", "log", "splunk", "splunk_ta_jboss_main.log"]
)
LOG_LEVEL_PARAMS = "-Dlevel="
LOG_LEVEL_VALUE = "INFO"
LOG4J_2_PROP_FILE = "-Dconfiguration_file="

META = "meta"
