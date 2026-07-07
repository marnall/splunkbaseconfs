#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

APP_NAME = "Splunk_TA_snow"

DEFAULT_RECORD_LIMIT = 3000
DEFAULT_DISPLAY_VALUE = "false"

FIELD_SEPARATOR = "||"
INDEX_LENGTH = 80

FILTER_PARAMETER_MIGRATION_STANZA = "filter_parameter_migration"
SETTINGS_CONF_FILE = "splunk_ta_snow_settings"

CHECKPOINT_COLLECTION_NAME = "Splunk_TA_snow_inputs_checkpointer"

CONNECTION_ERROR = "log_connection_error"
SERVER_ERROR = "log_server_error"
GENERAL_EXCEPTION = "log_exception"
CONFIGURATION_ERROR = "log_configuration_error"
SNOW_ERROR = "ta_snow_error"

LOGFILE_PREFIX = "splunk_ta"
DELAY_LIMIT = 300
