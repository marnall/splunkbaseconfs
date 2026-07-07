import os

APP_NAME = "jSonar Add-On for Splunk"
SPLUNK_HOME = os.environ['SPLUNK_HOME']

# App Configuration
CONFIGURATION_NAME = "sonar_configuration"
CONFIGURATION_STANZA = "sonar_service"
KEY = "key"
LABEL = "label"
ADDRESS_FIELD = "address"
ADDRESS_LABEL = "Sonar Service Address"
DESCRIPTION_FIELD = "description"
IS_DEFAULT_FIELD = "is_default"
PORT_FIELD = "port"
PORT_LABEL = "Sonar Service Port"
LIMIT_FIELD = "limit"
LIMIT_LABEL = "Sonar Search Limit"
LICENSE_FIELD = "license"
LICENSE_LABEL = "Sonar Service License"
INSTANCE_FIELD = "instance"
INSTANCES_FIELD = "instances"
PREV_INSTANCE_FIELD = "prev_instance"
REALM = "jSonar"

# Headers
SONAR_MESSAGE_HEADER = "sonar-message"
CONTENT_TYPE_HEADER = "Content-Type"
CONTENT_LENGTH_HEADER = "Content-Length"

# Sonar Splunk Request Body
INDEX = "index"
TIMESTAMP_FIELD = "timestampField"
START_TIME = "_startTime"
END_TIME = "_endTime"
USER = "user"
SEARCH_ID = "searchId"
STAGES = "commands"
SEARCH_STAGE = "search"
LIMIT_STAGE = "limit"
LICENSE = "license"
DISABLE_COUNT = "disableCount"

# Splunk Search
SEARCH_COMMANDS = "commands"
COMMAND_FIELD = "command"
ARGS_FIELD = "args"
SONAR_COMMAND = "sonar"
SEARCH_COMMAND = "search"
SPATH_COMMAND = "spath"
HEAD_COMMAND = "head"
SEARCH_ARG = "search"

# Logging
LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
LOGGING_STANZA_NAME = 'python'
LOGGING_FILE_NAME = 'sonar_addon_for_splunk.log'
BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
LOGGING_FORMAT = "%(asctime)s %(levelname)s\t%(module)s.%(funcName)s:%(lineno)d - %(message)s"
