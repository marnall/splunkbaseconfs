# File: ciscoasa_consts.py
#
# Copyright (c) 2014-2022 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
#
# Json keys
CISCOASA_JSON_DIRECTION = "direction"
CISCOASA_JSON_ACCESS_LIST = "access_list"
CISCOASA_JSON_INTERFACE = "interface"
CISCOASA_JSON_LINE = "line"
CISCOASA_JSON_SRC_MASK = "src_mask"
CISCOASA_JSON_DEST_MASK = "dest_mask"
CISCOASA_JSON_DEST = "dest"
CISCOASA_JSON_SRC = "src"
CISCOASA_JSON_IP_USERNAME = "username"
CISCOIOS_JSON_ENABLE_PASSWORD = "enable_password"  # pragma: allowlist secret
CISCOIOS_JSON_CMD = "command"
CISCOIOS_JSON_OUTPUT = "output"

# Success/Error messages
CISCOASA_ERR_CMD_EXEC = "Command execution failed"
CISCOASA_ERR_ASA_SRC_DEST_ANY = "Both Source and Dest can't be any"
CISCOASA_ERR_ASA_INVALID_DATA_ACCESS_GROUP = "Invalid data returned while querying for access-group"
CISCOASA_ERR_ASA_SSH_CONNECTION_FAILED = "Could not establish ssh connection to ASA device"
CISCOASA_SUCC_ASA_FOUND_ACCESS_LIST = "Found access-list"
CISCOASA_ERR_ASA_DUPLICATE_ACCESS_LIST = "Found an access-list named '{present_acl_name}' configured for the given interface '{intf}' and direction '{direction}', can't overwrite it with the given access-list '{acl_name}'. Please check the configuration"  # noqa
CISCOASA_SUCC_ASA_ACCESS_LIST_NOT_FOUND = "Access list not found"
CISCOASA_MSG_FROM_DEVICE = "Message from device:\n"
CISCOIOS_SUCC_CMD_EXEC = "Command execution successful"
CISCOIOS_ERR_READ_FROM_SERVER_FAILED = "Read from device failed"
CISCOIOS_ERR_SHELL_SEND_COMMAND = "On device execution of command '{}' failed"
CISCOIOS_ERR_SSH_CONNECTION_FAILED = "Could not establish ssh connection to Cisco IOS device"
CISCOIOS_ERR_CONNECTIVITY_TEST = "Test Connectivity Failed"
CISCOIOS_SUCC_CONNECTIVITY_TEST = "Test Connectivity Passed"
CISCOIOS_ERR_ENABLE_COMMAND_LOGIN_FAILED = "'enable' command login failed"
CISCOIOS_MSG_CHECK_YOUR_CREDENTIALS = "Please check your credentials"

# Progress messages
CISCOASA_PROG_ACCESS_LIST_VALIDATED = "Access List validated"
CISCOASA_PROG_GOT_TEXT = "Got text from device =  '{}'"
CISCOIOS_PROG_EXECUTING_CMD = "Executing command =  '{}'"
CISCOIOS_PROG_SENDING_ENABLE_CREDENTIALS = "Sending enable credentials"
CISCOIOS_PROG_EXECUTED_CMD = "Executed command =  '{}'"

# Other constants
CISCOIOS_CONST_ANY = "any"

# Timeouts in seconds
FIRST_RECV_TIMEOUT = 30
SECOND_ONWARDS_RECV_TIMEOUT = 1
SEND_TIMEOUT = 2

# The max number of bytes to read in Kb
MAX_RECV_BYTES_TO_READ = 5 * 1024

# Actions supported
ACTION_ID_GET_CONFIG = "get_config"
ACTION_ID_GET_VERSION = "get_version"
ACTION_ID_LIST_SESSIONS = "list_sessions"
ACTION_ID_TERMINATE_SESSION = "terminate_session"
ACTION_ID_BLOCK_IP = "block_ip"
ACTION_ID_UNBLOCK_IP = "unblock_ip"
