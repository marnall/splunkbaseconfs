"""
Primary Splunk App code for Duo connector. Implements log collection via the Duo Admin API for indexing
by Splunk as data inputs.

Copyright (c) 2023 Cisco Systems, Inc. and/or its affiliates
All rights reserved.
"""

from __future__ import print_function

import hashlib
import os
import shutil
import string
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lib"))
import xml.dom.minidom
import xml.sax.saxutils
import xml.etree.ElementTree as ET
import logging
import socket
from typing import Tuple, Dict, Optional, Union

import splunklib.client as client
from splunklib.modularinput import Scheme, Argument
import duo_client as duo_client
from logclasses import utils
from logclasses.paginated_administrator_log import PaginatedAdministratorLog
from logclasses.paginated_authentication_log import PaginatedAuthenticationLog
from logclasses.paginated_telephony_v2_log import PaginatedTelephonyV2Log
from logclasses.paginated_telephony_log import PaginatedTelephonyLog
from logclasses.paginated_account_log import PaginatedAccountLog
from logclasses.paginated_endpoint_log import PaginatedEndpointLog
from logclasses.paginated_trust_monitor_log import PaginatedTrustMonitorLog
from logclasses.paginated_authentication_v2_log import PaginatedAuthenticationV2Log
from logclasses.paginated_activity_log import PaginatedActivityLog

LOG_CLASSES = (
    PaginatedAccountLog,
    PaginatedActivityLog,
    PaginatedAdministratorLog,
    PaginatedTelephonyV2Log,
    PaginatedTelephonyLog,
    PaginatedAuthenticationLog,
    PaginatedEndpointLog,
    PaginatedTrustMonitorLog,
    PaginatedAuthenticationV2Log,
)

LOCAL_API_HOST = "api-duo1.duo.test"

# Define variable for masking sensitive data
SKEY_MASK = "--------"

NON_SCHEME_DEFAULTS = [
    'name',
    'stanza',
    'passAuth',
    'persistentQueueSize',
    'queueSize',
    'python.version',
    'logging_level'
]

DUO_LOG_OPTIONS = [
    'account',
    'activity',
    'administrator',
    'authentication',
    'authentication v2',
    'telephony',
    'telephony v2',
    'trust monitor',
    'endpoint'
]

LOGGER: logging.Logger = utils.create_and_configure_logger(__name__)


def get_scheme(output_format: str = "xml") -> Union[ET.Element, str]:
    """
    Function to craft and return a description of the duo_input scheme. The default is to return an
    XNL representation that Splunk uses for creating the new input UI page as well as
    storing/sending information for user defined inputs.

    The output_format argument can be passed as "input_spec" to generate a text listing of the
    information. This would be done primarily for creating the inputs.conf.spec file for the README
    folder before packaging the app for submission to Splunkbase.
    :param output_format: String value of "xml" (the default) or "input_spec" to indicate the
        format of the return object.
    :retval: XML object (default) or text
    """
    duo_input_scheme = Scheme("Duo Security Log Input")
    duo_input_scheme.description = "Get log data from the Duo Security Admin API."
    duo_input_scheme.use_external_validation = True
    duo_input_scheme.streaming_mode = Scheme.streaming_mode_simple

    # Allow for definition of multiple Duo Security Account Admin API data inputs
    #     within Splunk to support customers with multiple accounts and/or
    #     parent / child account relationships.
    #
    # Each duo_input defined in Splunk has a separate configuration for (api-hostname, ikey, skey).
    #     Splunk will launch a separate instance of this script for each input defined.
    duo_input_scheme.use_single_instance = False
    duo_input_spec = '[duo_input://default]\n'

    # Defines form label when configuring your Duo Splunk App.
    ikey_arg = Argument("ikey")
    ikey_arg.data_type = Argument.data_type_string
    ikey_arg.required_on_create = True
    duo_input_scheme.add_argument(ikey_arg)
    duo_input_spec += 'ikey = <value>\n'

    skey_arg = Argument("skey")
    skey_arg.data_type = Argument.data_type_string
    skey_arg.required_on_create = True
    duo_input_scheme.add_argument(skey_arg)
    duo_input_spec += 'skey = <value>\n'

    host_arg = Argument("api_host")
    host_arg.data_type = Argument.data_type_string
    host_arg.required_on_create = True
    duo_input_scheme.add_argument(host_arg)
    duo_input_spec += 'api_host = <value>\n'

    for log_option in DUO_LOG_OPTIONS:
        log_option_name = log_option.replace(' ', '_') + '_log'
        new_arg = Argument(log_option_name)
        new_arg.data_type = Argument.data_type_boolean
        duo_input_scheme.add_argument(new_arg)
        duo_input_spec += f"{log_option_name} = <value>\n"

    debug_arg = Argument("logging_level")
    debug_arg.data_type = Argument.data_type_string
    debug_arg.required_on_create = False
    duo_input_scheme.add_argument(debug_arg)
    duo_input_spec += 'logging_level = <value>\n'

    LOGGER.debug(duo_input_scheme)
    if output_format == 'xml':
        return duo_input_scheme.to_xml()
    elif output_format == 'input_spec':
        return duo_input_spec
    else:
        raise RuntimeError("Unknown output format requested.")


def do_scheme():
    print(ET.tostring(get_scheme(), encoding="utf-8", method="xml").decode("UTF-8"))


def print_error(s):
    """ Prints XML error data in a format suitable for Splunk """
    print(u'<error><message>{}</message></error>'.format(xml.sax.saxutils.escape(s)))


def encrypt_and_store_skey(session_key, ikey, skey):
    """Stores the skey in Splunk password storage"""
    args = {'token': session_key}
    service = client.connect(**args)
    for storage_password in service.storage_passwords:
        if storage_password.username == ikey:
            LOGGER.debug("Deleting existing skey for %s", ikey)
            service.storage_passwords.delete(
                username=storage_password.username)
            break
    LOGGER.debug("Storing encrypted skey for %s", ikey)
    service.storage_passwords.create(skey, ikey)


def mask_skey(session_key, input_name, config):
    """Access the local inputs.conf file and mask the skey value"""
    args = {'token': session_key}
    service = client.connect(**args)
    kind, input_name = input_name.split("://")
    item = service.inputs.__getitem__((input_name, kind))
    config['skey'] = SKEY_MASK
    item.update(**config).refresh()


def get_skey(session_key, ikey) -> Optional[str]:
    """
    Retrieve skey from encrypted Splunk password storage service.
    :raises LookupError if an skey for the given ikey is not found.
    """
    args = {'token': session_key}
    service = client.connect(**args)

    for storage_password in service.storage_passwords:
        if storage_password.username == ikey:
            return storage_password.content.clear_password

    raise LookupError(f"Unable to retrieve skey for ikey=[{ikey}]. "
                      "Setting config value for skey to None")


def get_config() -> Tuple[Dict[str, str], str]:
    """ Gets the admin api credentials from the configuration settings."""
    config = {}
    stanza_name = "unknown"
    config_str = sys.stdin.read()
    doc = xml.dom.minidom.parseString(config_str)
    root = doc.documentElement
    session_key = root.getElementsByTagName('session_key')[0].firstChild.data
    conf_node = root.getElementsByTagName('configuration')[0]
    if conf_node:
        LOGGER.debug('XML: found configuration')

        stanza = conf_node.getElementsByTagName('stanza')[0]
        if stanza:
            stanza_name = stanza.getAttribute('name')
            if stanza_name:
                LOGGER.debug("XML: found stanza: %s", stanza_name)
                config['name'] = stanza_name.replace('duo_input://', '')

                params = stanza.getElementsByTagName('param')
                for param in params:

                    param_name = param.getAttribute('name')
                    if (param_name and param.firstChild and
                            param.firstChild.nodeType == param.firstChild.TEXT_NODE):
                        data = param.firstChild.data
                        config[param_name] = data

                        if 'skey' in param_name:
                            log_data = '------' + data[-4:]
                        else:
                            log_data = data

                        LOGGER.debug('XML: "%s" -> "%s"', param_name, log_data)

    if not config:
        raise Exception('Invalid configuration received from Splunk.')

    if ('ikey' not in config or 'skey' not in config or
            'api_host' not in config):
        raise Exception('Config requires ikey, skey, and api_host')

    if config["skey"] != SKEY_MASK:
        LOGGER.debug("skey not masked. Starting encryption and storage.")
        encrypt_and_store_skey(session_key, config["ikey"], config["skey"])
        mask_skey(
            session_key,
            stanza_name,
            # Splunk errors when saving passAuth -- it is immutable
            dict(
                (idx, config[idx])
                for idx in config
                if idx not in NON_SCHEME_DEFAULTS
            )
        )

    config["skey"] = get_skey(session_key, config["ikey"])

    return config, session_key


def get_validation_data():
    """
    Parses the data the user has inputted to be validated.
    This data is sent in a different format than the config data.
    """
    val_data = {}
    val_str = sys.stdin.read()
    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement

    session_key = root.getElementsByTagName('session_key')[0].firstChild.data
    item_node = root.getElementsByTagName('item')[0]
    key = 'name'
    try:
        if item_node:
            val_data[key] = item_node.getAttribute(key)

            params_node = item_node.getElementsByTagName('param')
            for param in params_node:
                key = param.getAttribute('name')
                if key and param.firstChild:
                    val_data[key] = param.firstChild.data
    except Exception as e:
        LOGGER.error("Unable to validate user input field=%s: %s", key, e)

    #  Grab the masked skey in order to validate API credentials
    if val_data["skey"] == SKEY_MASK:
        val_data["skey"] = get_skey(session_key, val_data["ikey"])

    return val_data


def get_interval(config):
    """
    If the interval field is not a number, it's either a cron
    schedule, which we won't check, or an invalid interval
    which Splunk will catch. Set this to 120 so it passes validation
    """

    try:
        interval = int(config['interval'])
    except ValueError:
        #  XXX We will eventually need to make this work better with cron
        interval = 120

    return interval


def verify_integration_config(duo_admin, offset_seconds, unix_ts_now):
    """Verify the ikey, skey, and api-host by making two different adminapi
    calls. This method supports a mintime offset which is used to minify the
    amount of data queried. This method tests the account summary and the
    administrator logs admin api endpoint. These two are the minimum number of
    api endpoints that we need to call to verify that the admin has set "Grant
    read information" and "Grant read log" in the integration configuration.

    Args:
        duo_admin (duo_client.Admin): Instance of a duo_client object that can
                                      communicate with the adminapi. This can
                                      raise exceptions when attempting to pull
                                      logs.
        offset_seconds (int): The offset that will be added to the current ts
                              timestamp. This determines what the mintime query
                              offset is.
        unix_ts_now (int): The current time in seconds since epoch.

    Returns:
        None: This method simply runs instance methods on the duo_admin param,
              and bubbles up exceptions to the caller if the API call can't be
              made.

    """
    LOGGER.info("Verifying ikey, skey, and api-host with sample api calls.")
    mintime_seconds = unix_ts_now + offset_seconds

    LOGGER.info("Testing api call w/ get_info_summary")
    duo_admin.get_info_summary()

    LOGGER.info("Testing api call w/ get_administrator_log")
    duo_admin.get_administrator_log(mintime=mintime_seconds)


def validate_arguments(ikey: str, skey: str, host: str, interval: int, offset_seconds: int=-140):
    """
    Ensures that the provided credentials have access to different log types

    Also check that the interval is >= 120 seconds to avoid rate limiting.
    :param ikey: Integration key of Admin Panel API
    :param skey: Secret key of Admin Panel API
    :param host: Host of Admin Panel API
    :param interval: How often Splunk runs this input script, in seconds.
    :param offset_seconds: Number of seconds to subtract from current time, for the validation
            request
    """
    if interval < 120:
        LOGGER.error("The interval must be greater than or equal to 120 seconds")
        print_error('The interval must be greater than or equal to 120 seconds')
        raise ValueError("The interval must be greater than or equal to 120 seconds")

    admin = duo_client.admin.Admin(ikey=ikey, skey=skey, host=host)
    if host == LOCAL_API_HOST:
        admin.ca_certs = "DISABLE"

    current_unix_ts = int(time.time())

    try:
        verify_integration_config(admin, offset_seconds, current_unix_ts)

    # RuntimeError raised from duo_client.Admin calls that result in non-200
    # HTTP response statues. Using utils.log_exception to cram the traceback
    # into a single line because the traceback information doesn't appear in
    # the ModularInput log if it spans more than one line. Re-raising the
    # original exception to bubble that to the top.
    except RuntimeError as re:
        utils.log_exception(LOGGER, f"Admin API credentials failed to get logs: {re}")
        print_error("The provided admin API credentials cannot get the "
                    "necessary logs. Please verify that the Admin API settings "
                    "are correctly configured.")
        raise

    # Raised for hostnames that are incorrect.
    except socket.gaierror as se:
        utils.log_exception(LOGGER, f"Unable to connect to API host={host} for validation: {se}")
        print_error(
            f"Unable to connect to API host={host}. Check that your host is configured correctly."
        )
        raise

    # Log stacktrace when there are unhandled exceptions.
    except Exception as ex:
        utils.log_exception(LOGGER,
                            f"Unhandled exception when validating admin API credentials: {ex}")
        print_error(f"Unhandled exception when validating admin API credentials: {ex}")
        raise


def validate_input():
    """
    Method will build the configuration from the incoming XML via stdin, get
    the interval schedule from the configuration (defaults to 120s), and
    validates the configuration by making a few minimized Duo Admin API queries.
    """
    config = get_validation_data()
    interval = get_interval(config)
    validate_arguments(config['ikey'], config['skey'], config['api_host'], interval)


# This needs to be rewritten, or not even used at all. Smelly
def log_attribute_name(log_class_name: str):
    """
    Convert log class name into Splunk attribute name
    """
    new_string = []
    for i in range(1, len(log_class_name)):
        if log_class_name[i] in string.ascii_lowercase or log_class_name[i] in string.digits:
            new_string.append(log_class_name[i])
        elif log_class_name[i] in string.ascii_uppercase:
            new_string.append('_')
            new_string.append(log_class_name[i].lower())
    attribute_string = log_class_name[0].lower()
    attribute_string += ''.join(new_string)
    return attribute_string


def run_script():
    """
    Method will instantiate a duo_client.Admin object with the configured
    ikey/skey/api_host. In addition, it will call each log collector class to
    poll the Duo adminapi for JSON encoded data that gets written to stdout.
    """
    LOGGER.info("Getting input configuration.")
    config, splunk_session_key = get_config()
    LOGGER.info("Configuration processing completed. Setting LOGGER level for %s to %s",
                config['name'], config['logging_level'])
    LOGGER.setLevel(config['logging_level'])

    splunk_session_args = {
        'token': splunk_session_key,
        'user': 'nobody',
        'app': 'duo_splunkapp'
    }

    local_mode: bool = config['api_host'] == LOCAL_API_HOST

    admin_api = duo_client.Admin(
        ikey=config['ikey'],
        skey=config['skey'],
        host=config['api_host'],
        ca_certs="DISABLE" if local_mode else None,
        digestmod=hashlib.sha512
    )

    # Why not just let the log class define the endpoint name? Look into why this was needed
    timestamp_path = os.path.dirname(os.path.abspath(__file__))
    for logclass in LOG_CLASSES:
        log_name: str = logclass.__name__
        try:
            log_name = log_attribute_name(logclass.__name__.replace('Paginated', ''))
            # Check if logs should be pulled for a "logclass" based on configuration setting
            if config[log_name] == "1":
                LOGGER.info("Starting collector for %s", logclass.__name__)
                log = logclass(admin_api, timestamp_path, splunk_session_args, config)
                log.run()
        except Exception as ex:
            LOGGER.error("Unable to process [%s] logs: %s", log_name, ex)

    LOGGER.info("Ending execution for %s.", config['name'])


def main():
    # Main entry point for duo_splunkapp execution. The first step is to set up logging
    # to a dedicated folder/file
    LOGGER.info("Starting %s...", __file__)

    if len(sys.argv) > 1:
        try:
            if sys.argv[1] == '--scheme':
                LOGGER.info("Calling get_scheme('xml')")
                ET.dump(get_scheme())
                LOGGER.info("Scheme XML output completed. Exiting.")
            elif sys.argv[1] == '--input-spec':
                LOGGER.info("Calling get_scheme('input_spec')")
                print(get_scheme("input_spec"))
            elif sys.argv[1] == '--validate-arguments':
                LOGGER.info("Validating input")
                validate_input()
                LOGGER.info("Input validation completed. Exiting.")
            else:
                pass
        except Exception as ex:
            print_error(f"Failed to get inputconfig: {ex}")
            LOGGER.error("Failed to get input config: %s", ex)
    else:
        try:
            LOGGER.info("Running script")
            run_script()
        except Exception as ex:
            LOGGER.error("Failed to run duo_input connector app: %s", ex)


if __name__ == '__main__':
   main()
