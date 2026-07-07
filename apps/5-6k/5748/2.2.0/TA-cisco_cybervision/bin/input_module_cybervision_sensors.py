import time
import datetime
import splunk.version as ver
import TA_cisco_cybervision_utils as utils
import requests


def get_checkpoint_key(helper):
    stanza_name = helper.get_input_stanza_names()
    cp_key = f"sfdc_streaming_api_fdse_events://{stanza_name}"
    helper.log_debug(f"Inquiring checkpoint key: {cp_key}")
    return cp_key


def get_checkpoint(helper, cp_key):
    checkpoint = helper.get_check_point(cp_key)
    helper.log_debug(f"Retrieved checkpoint for {cp_key}: {checkpoint}")
    return checkpoint


def set_checkpoint(helper, cp_key, value):
    helper.log_debug(f"Setting checkpoint for {cp_key} to {value}")
    helper.save_check_point(cp_key, value)


def validate_input(helper, definition):
    global_account = definition.parameters.get("global_account", None)
    error_msg_prefix = "Cyber Vision Error: "

    utils.validate_global_account(helper, global_account, error_msg_prefix)


def collect_events(helper, ew):
    input_name = helper.get_input_stanza_names()
    dc_starting_time = datetime.datetime.now()
    helper.log_info(
        f"Starting data collection for input {input_name} at {dc_starting_time}"
    )
    global_account = helper.get_arg("global_account")
    if not global_account:
        raise utils.InvalidGlobalAccount(
            "Invalid global_account for input '{}'.".format(input_name)
        )

    api_token = global_account.get("api_token")
    server_address = global_account.get("ip_address")
    verify_ssl = utils.verify_ssl(global_account)
    # stanza_name = str(helper.get_input_stanza_names())
    # current_time = int(time.time() * 1000)
    splunk_version = ver.__version__
    if not splunk_version:
        helper.log_error("Cisco Cyber Vision Error: unable to fetch splunk version.")
        return
    # Fetching proxy data
    proxy_dict = helper.get_proxy()
    proxy_uri = None
    if proxy_dict:
        proxy_uri = utils.format_proxy_uri(proxy_dict)
    proxy_settings = {"http": proxy_uri, "https": proxy_uri}

    # # Storing necessary data into dictionary
    config_details = {}
    config_details["server_address"] = server_address
    if not server_address.startswith("https"):
        helper.log_error(
            "Unsuccessfully terminating the data collection.Reason: "
            "Server address should start with https. Found {}".format(server_address)
        )
        exit(1)
    host_name = server_address.split("https://")[1]
    config_details["user_agent"] = "Splunk/{}".format(splunk_version)
    config_details["proxy_settings"] = proxy_settings
    config_details["verify_ssl"] = verify_ssl
    config_details["api_token"] = api_token
    config_details["api_version"] = "3.0"
    sourcetype = "cisco:cybervision:sensors"

    sensor_list = utils.request_get(
        helper=helper, endpoint="/sensors", config_details=config_details, params=None
    )
    additional_fields = {}
    additional_fields["host"] = host_name
    utils.ingest_in_splunk(
        helper=helper,
        ew=ew,
        records=sensor_list,
        sourcetype=sourcetype,
        additional_fields=additional_fields,
        source="Sensors",
    )

    helper.log_info(
        f"Data collection for input {input_name} at {dc_starting_time} completed."
    )
