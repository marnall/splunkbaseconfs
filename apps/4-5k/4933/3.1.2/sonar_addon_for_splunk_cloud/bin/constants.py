#!/usr/bin/env python
# -*- coding: utf-8 -*-

APP_NAME = "jSonar Add-On for Splunk"

# App Configuration
CONFIGURATION_NAME = "sonar_configuration"
CONFIGURATION_STANZA = "sonar_service"
KEY = "key"
LABEL = "label"
ADDRESS_FIELD = "address"
ADDRESS_LABEL = "Sonar Service Address"
PORT_FIELD = "port"
PORT_LABEL = "Sonar Service Port"
LIMIT_FIELD = "limit"
LIMIT_LABEL = "Sonar Search Limit"
LICENSE_FIELD = "license"
LICENSE_LABEL = "Sonar Service License"
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

