"""Collect the data from Cisco servers."""

# All rights reserved
import sys
import os
import json
from datetime import datetime
import splunk.entity as entity
import splunk.rest as rest
import xml.sax.saxutils as xss

import urllib3
import logger_manager
import exceptions
from splunk.clilib import cli_common as cli

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logger_manager.get_logger("collect")

APP_DIR_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
APP_NAME = __file__.split(os.sep)[-3]

try:
    utils_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "utils")

    sys.path.extend([utils_path])

    from nxapi_utils import NXAPITransport
except Exception as e:
    logger.error("Nexus Error: Error importing the required module: %s", str(e))
    raise


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S%z"

# Global Variables.
cmdFile = ""
command = ""
dev_ip = ""
device = ""
proxy_scheme = ""


def get_ssl_config():
    """Get the SSL config details provided by the user."""
    verify_ssl = True
    ca_certs_path = None
    try:
        cfg_stanza = cli.getAppConf("cisco_nexus_setup", "TA_cisco-Nexus-9k")
        cfg = cfg_stanza.get("ssl_verification", {})
        verify_ssl = str(cfg.get("verify_ssl")).upper()

        if verify_ssl == "FALSE":
            verify_ssl = False
        elif verify_ssl == "TRUE":
            verify_ssl = True

        ca_certs_path = str(cfg.get("ca_certs_path").strip())
    except Exception:
        logger.exception("Error occurred while getting SSLConfig.")

    if not verify_ssl:
        logger.debug("SSL Verification is set to False.")
        ssl_config = False
    elif verify_ssl and ca_certs_path:
        logger.debug(
            "SSL Verification is set to True and will use the cert from this path. %s.",
            ca_certs_path,
        )
        ssl_config = ca_certs_path
    else:
        logger.debug("SSL Verification is set to True.")
        ssl_config = True

    return ssl_config


""" Display data in JSON format"""


def _display_data(device, component, json_element):
    events_collected = 0
    json_row = json.dumps(json_element, ensure_ascii=False)
    row_string = json.loads(json_row)
    if type(row_string) is dict:
        for key, value in list(row_string.items()):
            if (
                value is not None
                and type(value) not in [list, tuple, dict]
                and value.startswith('"')
                and value.endswith('"')
            ):
                value = value[1:-1]
                row_string[key] = value
    current_time = datetime.now().strftime(TIMESTAMP_FORMAT)
    response = {
        "timestamp": current_time,
        "component": component,
        "device": device,
        "Row_info": row_string,
    }
    print(json.dumps(response, ensure_ascii=False))
    events_collected += 1
    return events_collected


""" Split JSON response"""


def _split_json(device, component, json_data, table_name, row_name):
    events_collected = 0
    if table_name in json_data:
        single_row = json_data[table_name][row_name]
        if type(single_row) is list:
            for element in single_row:
                events_collected += _display_data(device, component, element)
        elif type(single_row) is dict:
            events_collected += _display_data(device, component, single_row)
    return events_collected


def _collect_data(command, device):
    try:
        logger.info(
            "Starting to collect data for device %s for command '%s'.", device, command
        )
        cmd_out = NXAPITransport.clid(command)
    except Exception as e:
        raise exceptions.Nexus9kError(
            "Nexus Error: Not able to Execute command through NXAPI: %s : DEVICE IP: %s"
            % (str(e), str(device))
        )

    return cmd_out


def _collect_table_info(data_keys, table_names, row_names, component, cmd_json, device):
    events_collected = 0
    for table in data_keys:
        if "TABLE" in table:
            table_names.append(table)
            row = table.replace("TABLE", "ROW")
            row_names.append(row)

    for i in range(len(table_names)):
        events_collected += _split_json(
            device, component, cmd_json, table_names[i], row_names[i]
        )

    return events_collected


def _collect_internal_keys_info(internal_single_row, device, component):
    events_collected = 0
    internal_data_keys = list(internal_single_row.keys())
    internal_table_names = []
    internal_row_names = []
    for table in internal_data_keys:
        if "TABLE" not in table:
            internal_value = internal_single_row[table]
            if type(internal_value) is dict:
                current_time = datetime.now().strftime(TIMESTAMP_FORMAT)
                response = {
                    "timestamp": current_time,
                    "component": component,
                    "device": device,
                    "Row_info": internal_single_row[table],
                }
                print(json.dumps(response, ensure_ascii=False))
                events_collected += 1
            else:
                current_time = datetime.now().strftime(TIMESTAMP_FORMAT)
                internal_key_value = {table: internal_value}
                response = {
                    "timestamp": current_time,
                    "component": component,
                    "device": device,
                    "Row_info": internal_key_value,
                }
                print(json.dumps(response, ensure_ascii=False))
                events_collected += 1

        if "TABLE" in table:
            internal_table_names.append(table)
            row = table.replace("TABLE", "ROW")
            internal_row_names.append(row)

    for i in range(len(internal_table_names)):
        events_collected += _split_json(
            device,
            component,
            internal_single_row,
            internal_table_names[i],
            internal_row_names[i],
        )

    return events_collected


""" execute CLI"""


def _execute_command(command, device, component="N/A"):
    cmd_out = _collect_data(command, device)

    if cmd_out:
        cmd_json = json.loads(cmd_out)
    events_collected = 0
    if cmd_json is not None:
        data_keys = list(cmd_json.keys())
        row_key_val = []
        for i in range(len(data_keys)):
            if "TABLE" not in data_keys[i]:
                check_type = cmd_json[data_keys[i]]
                if type(check_type) is dict:
                    internal_single_row = cmd_json[
                        data_keys[i]
                    ]  # single_row  has inside raw data in k:v pair

                    events_collected += _collect_internal_keys_info(
                        internal_single_row, device, component
                    )
                else:
                    value = cmd_json[data_keys[i]]
                    key_value = {data_keys[i]: value}
                    row_key_val.append(key_value)
        if row_key_val:
            events_collected += _display_data(device, component, row_key_val)
        table_names = []
        row_names = []

        events_collected += _collect_table_info(
            data_keys, table_names, row_names, component, cmd_json, device
        )

    logger.info(
        "Collected total=%d events for device %s for command '%s'.",
        events_collected,
        device,
        command,
    )


def _get_credentials(session_key):
    try:
        # list all credentials
        entities = entity.getEntities(
            ["admin", "passwords"],
            namespace=APP_NAME,
            owner="nobody",
            sessionKey=session_key,
        )
    except Exception as e:
        logger.error(
            "Nexus Error: Could not get %s credentials from splunk. Error: %s"
            % (APP_NAME, str(e))
        )

    # return first set of credentials
    device_credentials = dict()
    for i, c in list(entities.items()):
        if (str(c["eai:acl"]["app"])) == APP_NAME:
            device_splitted_values = i.split(":")[0].split(",")
            device = device_splitted_values[0]
            try:
                port = str(int(device_splitted_values[1]))
            except Exception:
                port = None
            if port:
                device = ":".join([device, port])
            username = xss.unescape(c["username"])
            password = c["clear_password"]
            credential = []
            credential = [username, password]
            device_credentials[device] = list(credential)
    return device_credentials


def _execute_command_without_component(command, device):
    try:
        _execute_command(command=command, device=device)
    except Exception as e:
        logger.error(
            "Error occurred while collecting the data. Error: %s.", str(e)
        )


def _prepare_and_execute(session_key):
    global command, cmdFile, proxy_scheme
    device_credentials = _get_credentials(session_key)
    for device in list(device_credentials.keys()):
        username = device_credentials[device][0]
        password = device_credentials[device][1]
        target_url = proxy_scheme + "://" + str(device) + "/ins"
        try:
            NXAPITransport.init(
                target_url=target_url,
                username=username,
                password=password,
                timeout=600,
                verify=get_ssl_config(),
            )
        except Exception as e:
            logger.error(
                "Nexus Error: Not able to connect to NXAPI: %s, DEVICE IP: %s",
                str(e),
                str(device),
            )
            continue
        if cmdFile:
            cmdFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), cmdFile)
            file = open(cmdFile, "r")
            cmd_list = file.readlines()
            for cmd_in in cmd_list:
                try:
                    cmd_in = cmd_in.strip()
                    (cmd_in, component) = cmd_in.split(",")
                    cmd_in = cmd_in.strip()
                    _execute_command(command=cmd_in, device=device, component=component)
                except Exception as e:
                    logger.error(
                        "Error occurred while collecting the data. Error: %s.", str(e)
                    )
        elif command:
            _execute_command_without_component(command, device)


def get_proxy_scheme(session_key):
    """
    Get the HTTP_SCHEME configured in local/cisco_nexus_setup.conf OR default/cisco_nexus_setup.conf.

    return: http_scheme
    """
    _, res = rest.simpleRequest(
        "/servicesNS/nobody/" + APP_NAME + "/configs/conf-cisco_nexus_setup/SCHEME",
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )
    res_json = json.loads(res)
    scheme = res_json.get("entry", [{}])[0].get("content", {}).get("HTTP_SCHEME")
    return scheme


""" main method """


def main(argv):
    """Start the data collection for the executed command."""
    try:
        global proxy_scheme
        session_key = sys.stdin.readline().strip()
        if len(session_key) == 0:
            logger.error("Nexus Error: Did not receive a session key from splunkd.")
            sys.exit()
        proxy_scheme = get_proxy_scheme(session_key)
    except Exception as e:
        logger.error(
            "Nexus Error: Unable to read proxy scheme from cisco_nexus_setup.conf. Error: {0}".format(
                e
            )
        )
        logger.error("Nexus Error: Defaulting to https.")
        proxy_scheme = "https"
    length_of_argv = len(argv)
    if _validate_argumnets(argv):
        _parse_command_line_arguments(argv, length_of_argv, session_key)
        _execute(argv, length_of_argv, session_key)


""" Validate command line arguments """


def _validate_argumnets(argv):
    for a in argv:
        if not a:
            logger.error(
                "Nexus Error: Empty argument found. Please provide appropriate command line arguments."
            )
            return False
    return True


def _parse_extra_command_line_arguments(argv):
    global command, dev_ip
    if argv[0] == "-cmd":
        command = argv[1]
    if argv[2] == "-device":
        dev_ip = argv[3]


# Parse command line arguments.


def _parse_command_line_arguments(argv, length_of_argv, session_key):
    global cmdFile, command, dev_ip, inputcsv
    if length_of_argv > 1:
        try:
            if length_of_argv == 2:
                if argv[0] == "-inputFile":
                    cmdFile = argv[1]
                elif argv[0] == "-cmd":
                    command = argv[1]
            elif length_of_argv > 2:
                _parse_extra_command_line_arguments(argv)
        except Exception as e:
            logger.error("Nexus Error: Please enter valid arguments. %s", str(e))
            raise
    else:
        logger.error("Nexus Error: Unrecognized command line arguments")
        sys.exit()


""" execute method has following user input category:
    a) devices b) cmdFile c) command
"""


def _execute_command_for_device(device_credentials, dev_ip_arr):
    global dev_ip, command, device, proxy_scheme
    for device in list(device_credentials.keys()):
        for ip in dev_ip_arr:
            if ip == device:
                username = device_credentials[device][0]
                password = device_credentials[device][1]
                target_url = proxy_scheme + "://" + str(device) + "/ins"
                try:
                    NXAPITransport.init(
                        target_url=target_url,
                        username=username,
                        password=password,
                        timeout=600,
                        verify=get_ssl_config(),
                    )
                except Exception as e:
                    logger.error(
                        "Not able to connect to NXAPI: %s, DEVICE IP: %s",
                        str(e),
                        str(ip),
                    )
                _execute_command(command=command, device=ip)


def _execute(argv, length_of_argv, session_key):
    global dev_ip, credential_file, command, device, inputcsv, cmdFile, proxy_scheme
    if length_of_argv > 2:
        """Will execute if user input is device(s)"""
        if dev_ip:
            dev_ip_arr = dev_ip.split(",")
            device_credentials = _get_credentials(session_key)
            _execute_command_for_device(device_credentials, dev_ip_arr)
        else:
            _prepare_and_execute(session_key)
    else:
        """Will execute if user input is cmdFile"""
        """ Will execute if user input is command """
        _prepare_and_execute(session_key)


if __name__ == "__main__":
    logger.info("Data collection started.")
    try:
        main(sys.argv[1:])
    except Exception:
        logger.exception("Error in data collection.")

    logger.info("Data collection ended.")
