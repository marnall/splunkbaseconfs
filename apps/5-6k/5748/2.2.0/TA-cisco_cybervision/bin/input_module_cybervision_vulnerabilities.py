# encoding = utf-8

import time
import datetime
import splunk.version as ver
import TA_cisco_cybervision_utils as utils

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""


def validate_input(helper, definition):
    global_account = definition.parameters.get("global_account", None)
    interval = definition.parameters.get("interval")
    helper.log_debug("Cyber Vision Debug: interval is " + str(interval))
    error_msg_prefix = "Cyber Vision Error: "

    if not global_account:
        msg = "global account not found. Please add the valid global account."
        helper.log_error(error_msg_prefix + msg)
        raise ValueError(msg)


def collect_events(helper, ew):

    PAGE_SIZE = 50000  # Provided by Engineering

    try:
        input_name = helper.get_input_stanza_names()
        dc_starting_time = datetime.datetime.now()
        helper.log_info(
            "Starting data collection for input {} at {}".format(
                input_name, dc_starting_time
            )
        )

        global_account = helper.get_arg("global_account")
        if not global_account:
            raise utils.InvalidGlobalAccount(
                "Invalid global_account for input '{}'.".format(input_name)
            )

        api_token = global_account.get("api_token")
        server_address = global_account.get("ip_address")
        verify_ssl = utils.verify_ssl(global_account)
        stanza_name = str(helper.get_input_stanza_names())
        current_time = int(time.time() * 1000)
        splunk_version = ver.__version__
        if not splunk_version:
            helper.log_error(
                "Cisco Cyber Vision Error: unable to fetch splunk version."
            )
            return
        # Fetching proxy data
        proxy_dict = helper.get_proxy()
        proxy_uri = None
        if proxy_dict:
            proxy_uri = utils.format_proxy_uri(proxy_dict)
        proxy_settings = {"http": proxy_uri, "https": proxy_uri}

        # Storing necessary data into dictionary
        config_details = {}
        config_details["server_address"] = server_address
        if not server_address.startswith("https"):
            helper.log_error(
                "Unsuccessfully terminating the data collection. Reason: Server address "
                "should start with https. Found {}".format(server_address)
            )
            exit(1)
        host_name = server_address.split("https://")[1]
        config_details["user_agent"] = "Splunk/{}".format(splunk_version)
        config_details["stanza"] = stanza_name
        config_details["proxy_settings"] = proxy_settings
        config_details["verify_ssl"] = verify_ssl
        config_details["api_token"] = api_token
        config_details["api_version"] = "3.0"
        config_details["end_date"] = current_time
        sourcetype = "cisco:cybervision:vulnerabilities"
        page = 1

        while True:
            params = {"page": page, "size": PAGE_SIZE}
            data = utils.request_get(helper, "vulnerabilities", config_details, params)
            if data and (page == 1):
                cve = data[0]["cve"]
                config_details["end_date"] = cve
            page += 1
            additional_fields = {}
            additional_fields["host"] = host_name
            additional_fields["time_field"] = "publishTime"

            utils.ingest_in_splunk(
                helper,
                ew,
                data,
                sourcetype,
                additional_fields,
                source="Vulnerabilities",
            )
            if len(data) < PAGE_SIZE:
                break

        helper.log_info(
            "Data collection process is completed for input {}".format(input_name)
        )
        helper.log_info(
            "Total time taken in data collection for input {} is {} seconds".format(
                input_name, (datetime.datetime.now() - dc_starting_time).total_seconds()
            )
        )
    except utils.InvalidGlobalAccount as e:
        helper.log_error(utils.DATA_COLLECTION_ERROR.format("Vulnerabilities", e))
        helper.log_error(utils.DATA_COLLECTION_TERMINATION)
        exit(1)
    except Exception as e:
        helper.log_error(utils.DATA_COLLECTION_ERROR.format("Vulnerabilities", e))
        helper.log_error(utils.DATA_COLLECTION_TERMINATION)
        exit(1)
