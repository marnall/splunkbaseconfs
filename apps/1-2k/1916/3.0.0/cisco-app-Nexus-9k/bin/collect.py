"""Collect the data from Cisco servers."""

# Copyright (C) 2024 Cisco Systems Inc.
# All rights reserved
import json
import os
import sys
import xml.sax.saxutils as xss
from datetime import datetime

import exceptions
import logger_manager
import splunk.rest as rest
import urllib3
from splunk.clilib import cli_common as cli

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logger_manager.get_logger("collect")

APP_NAME = __file__.split(os.sep)[-3]


try:
    utils_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "utils")

    sys.path.extend([utils_path])

    from nxapi_utils import NXAPITransport

except Exception as e:
    logger.error("Nexus Error: Error importing the required module: %s", str(e))
    raise


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S%z"

# Global variables.
command = ""
dev_ip = ""
device = ""
input_username = ""
input_password = ""
proxy_scheme = ""


def get_ssl_config():
    """Get the SSL config details provided by the user."""
    verify_ssl = True
    ca_certs_path = None
    try:
        cfg_stanza = cli.getAppConf("cisco_nexus_setup", "cisco-app-Nexus-9k")
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


""" execute CLI"""


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


def _collect_table_info(data_keys, table_names, row_names, component, cmd_json):
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


def _execute_command(command, device, component="N/A"):
    cmd_out = _collect_data(command, device)

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
            data_keys, table_names, row_names, component, cmd_json
        )

    logger.info(
        "Collected total=%d events for device %s for command '%s'.",
        events_collected,
        device,
        command,
    )


""" prepare execution """


def _prepare_and_execute():
    global command, proxy_scheme
    num_of_times_in_loop = 0
    num_of_times_exception_raised = 0
    exception_message = ""
    try:
        device_credentials = json.loads(sys.argv[1])
        for device in list(device_credentials.keys()):
            num_of_times_in_loop += 1
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
                    "Nexus Error: Not able to connect to the NXAPI: %s DEVICE IP: %s"
                    % (str(e), str(device))
                )
            try:
                _execute_command(command=command, device=device)
            except exceptions.Nexus9kError as e:
                logger.exception("Error raised while collecting data.")
                num_of_times_exception_raised += 1
                exception_message += str(e) + "\t"
            except Exception as e:
                logger.exception("Error raised while collecting the data.")
                num_of_times_exception_raised += 1
                exception_message += str(e) + "\t"

        # condition holds true when all IP address are incorrect
        if num_of_times_exception_raised == num_of_times_in_loop:
            logger.error(exception_message)
            print(exception_message)

    except Exception as err:
        logger.exception("Nexus Error: Not able to execute command.")
        raise err


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


def main(argv):
    """Start the data collection for the executed command."""
    try:
        global proxy_scheme
        session_key = sys.argv[2]
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
        _parse_command_line_arguments(argv, length_of_argv)
        _execute(argv, length_of_argv)


def _validate_argumnets(argv):
    """Validate command line arguments."""
    for a in argv:
        if not a:
            logger.error(
                "Nexus Error: Empty argument found. Please provide appropriate command line arguments."
            )
            return False
    return True


def _parse_extra_command_line_arguments(argv, length_of_argv):
    """Parse extra command line arguments."""
    global command, dev_ip, input_username, input_password
    if argv[0] == "-cmd":
        command = argv[1]
        if argv[2] == "-device":
            dev_ip = argv[3]
    if argv[0] == "-u":
        input_username = argv[1]
        input_password = argv[3]
        command = argv[5]
        dev_ip = argv[7]


def _parse_command_line_arguments(argv, length_of_argv):
    """Parse command line arguments."""
    global command, dev_ip, input_username, input_password
    if length_of_argv > 1:
        try:
            if length_of_argv == 2 and argv[0] == "-cmd":
                command = argv[1]
            elif length_of_argv > 2:
                _parse_extra_command_line_arguments(argv, length_of_argv)
        except Exception as e:
            logger.error("Nexus Error: Please enter valid arguments.%s", str(e))
            raise
    else:
        logger.error("Nexus Error: Unrecognized command line arguments")
        sys.exit()


def _init_nxapi_transport(ip, username, password, target_url):
    """Init NXAPI Transport."""
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
            "Nexus Error: Not able to connect to NXAPI: %s DEVICE IP: %s"
            % (str(e), str(ip))
        )


def _execute_with_username(
    dev_ip_arr, command, input_username, input_password, proxy_scheme
):
    num_of_times_in_loop = 0
    num_of_times_exception_raised = 0
    exception_message = ""
    for ip in dev_ip_arr:
        num_of_times_in_loop += 1
        target_url = f"{proxy_scheme}://{ip}/ins"
        _init_nxapi_transport(ip, input_username, input_password, target_url)
        try:
            _execute_command(command=command, device=ip)
        except exceptions.Nexus9kError as e:
            logger.error("Error raised while collecting data from Nexus 9k: %s", str(e))
            num_of_times_exception_raised += 1
            exception_message += str(e) + "\t"
        except Exception as e:
            logger.error("Error raised while collecting the data: %s", str(e))
            num_of_times_exception_raised += 1
            exception_message += str(e) + "\t"

    return num_of_times_in_loop, num_of_times_exception_raised, exception_message


def _execute_without_username(dev_ip_arr, command, proxy_scheme):
    device_credentials = json.loads(sys.argv[1])
    test_ip_credentials = False
    num_of_times_in_loop = 0
    num_of_times_exception_raised = 0
    exception_message = ""
    for device in list(device_credentials.keys()):
        device = xss.unescape(device)
        for ip in dev_ip_arr:
            if ip == device:
                num_of_times_in_loop += 1
                test_ip_credentials = True
                username = device_credentials[device][0]
                password = device_credentials[device][1]
                target_url = f"{proxy_scheme}://{device}/ins"
                _init_nxapi_transport(ip, username, password, target_url)
                try:
                    _execute_command(command=command, device=ip)
                except exceptions.Nexus9kError as e:
                    logger.error(
                        "Error raised while collecting the data from Nexus 9k: %s",
                        str(e),
                    )
                    num_of_times_exception_raised += 1
                    exception_message += str(e) + "\t"
                except Exception as e:
                    logger.error(
                        "Error raised while collecting the data from Nexus 9k: %s",
                        str(e),
                    )
                    num_of_times_exception_raised += 1
                    exception_message += str(e) + "\t"

    if not test_ip_credentials:
        logger.error("Entered IP Address is not Available.")

    return num_of_times_in_loop, num_of_times_exception_raised, exception_message


def _execute(argv, length_of_argv):
    """Execute method has following user input category: a) devices b) command."""
    global dev_ip, command, device, input_username, input_password, proxy_scheme
    num_of_times_in_loop = 0
    num_of_times_exception_raised = 0
    exception_message = ""
    if length_of_argv > 2:
        """Will execute if user input is device(s)"""
        if dev_ip:
            dev_ip_arr = dev_ip.split(",")
            if input_username:
                (
                    num_of_times_in_loop,
                    num_of_times_exception_raised,
                    exception_message,
                ) = _execute_with_username(
                    dev_ip_arr, command, input_username, input_password, proxy_scheme
                )

            else:
                (
                    num_of_times_in_loop,
                    num_of_times_exception_raised,
                    exception_message,
                ) = _execute_without_username(dev_ip_arr, command, proxy_scheme)

            # Will execute if we cannot connect to any of the IP address/s
            if num_of_times_exception_raised == num_of_times_in_loop:
                logger.error(exception_message)

    else:
        """Will execute if user input is command"""
        _prepare_and_execute()


if __name__ == "__main__":
    logger.debug("Data collection started.")
    main(sys.argv[3:])
    logger.debug("Data collection ended.")
