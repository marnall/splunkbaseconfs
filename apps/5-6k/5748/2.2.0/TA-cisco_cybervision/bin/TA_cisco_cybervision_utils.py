import json
import time
import datetime
import calendar
import requests
import os
import re
from solnlib.utils import is_true

import import_declare_test

VERIFY_SSL = True
DATA_COLLECTION_TERMINATION = (
    "Cisco Cyber Vision Error: failed to complete data collection and terminated."
)
DATA_COLLECTION_ERROR = "Cisco Cyber Vision Error: while collecting {} data: {}"
CERT_FILE_LOC = os.path.join(
    os.environ.get("SPLUNK_HOME"),
    "etc",
    "apps",
    import_declare_test.ta_name,
    "local",
    "custom_certs",
    "{cert_name}_cert.pem",
)


class InvalidGlobalAccount(Exception):
    """Exception Class for global account."""

    pass


def request_get(helper, endpoint, config_details, params=None):
    """
    Makes request to CyberVision.

    :param endpoint: endpoint to fetch data
    :param config_details: Basic configuration details
    :param params: request parameters
    :return records received in response, continuation_token
    """
    header_data = {
        "x-token-id": config_details.get("api_token"),
        "User-Agent": config_details.get("user_agent"),
    }
    api_version = config_details["api_version"]
    server_address = config_details.get("server_address")
    proxy_settings = config_details.get("proxy_settings")
    verify_ssl = config_details.get("verify_ssl")
    url = "{}/api/{}/{}".format(server_address, api_version, endpoint)

    helper.log_debug(
        f"Cyber Vision Debug: Sending request to Cyber Vision at URL: {url}."
    )

    response = requests.get(
        url,
        params=params,
        headers=header_data,
        verify=verify_ssl,
        proxies=proxy_settings,
    )
    response.raise_for_status()

    helper.log_debug(
        f"Cyber Vision Debug: Response received successfully from Cyber Vision endpoint {url}. Status Code: {response.status_code}"
    )

    data = json.loads(response.text)
    # helper.log_info("data = {}".format(data))
    return data


def get_checkpoint(helper, config_details, sourcetype, endpoint):
    """
    Function to initialize checkpoint for particular sourcetype of particular input.

    :param helper: object of BaseModInput class
    :param config_details: Basic configuration details
    :param sourcetype: Splunk Sourcetype to get checkpoint
    :param endpoint: REST endpoint to get data
    """
    stanza_name = config_details.get("stanza")
    sourcetype = sourcetype.split(":")[-1]
    endpoint = endpoint.split("/")[-1]
    checkpoint_name = stanza_name + "_" + sourcetype + "_" + endpoint

    start_date = helper.get_arg("start_date")
    if start_date:
        time_pattern = "%Y-%m-%dT%H:%M:%SZ"
        try:
            start_date = calendar.timegm(time.strptime(start_date, time_pattern))
        except Exception:
            helper.log_error(
                "CyberVision Error: Start date is not in format %Y-%m-%dT%H:%M:%SZ"
            )
            exit(1)
        start_date = int(start_date * 1000)
    else:
        start_date = config_details.get("end_date") - (
            7 * 86400 * 1000
        )  # 7 Days in Milliseconds
    checkpoint_time = helper.get_check_point(checkpoint_name)
    start_date = checkpoint_time if checkpoint_time else start_date

    config_details["start_date"] = start_date
    config_details["checkpoint_name"] = checkpoint_name


def update_checkpoint(helper, config_details):
    """
    Function to update checkpoint for particular sourcetype of particular input.

    :param helper: object of BaseModInput class
    :param config_details: Basic configuration details
    """
    end_date = config_details.get("end_date")
    checkpoint_name = config_details.get("checkpoint_name")
    helper.save_check_point(checkpoint_name, end_date)
    helper.log_debug(
        "CyberVision Debug: checkpoint updated for " + checkpoint_name + "."
    )


def ingest_in_splunk(helper, ew, records, sourcetype, additional_fields, source=None):
    """
    Ingests Records to Splunk.

    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    :param records: Records to be ingested in Splunk
    :param sourcetype: Sourcetype for Splunk Ingestion
    :param additional_fields: Dictionary of required fields to be added in record.
    """
    for record in records:
        index_time = record.get(additional_fields.get("time_field"))
        host = None
        if "host" in additional_fields:
            host = additional_fields["host"]
        if index_time:
            if not is_time_format(index_time):
                index_time = int(index_time) / 1000.0
            else:
                index_time = convert_to_epoch(index_time)
        else:
            index_time = time.time()

        event = helper.new_event(
            time=index_time,
            index=helper.get_output_index(),
            sourcetype=sourcetype,
            source=source,
            data=json.dumps(record, ensure_ascii=False),
            host=host,
        )
        ew.write_event(event)


def is_time_format(input):
    """Returns boolean value after checking whether the given input is in time format or not."""
    try:
        time.strptime(str(input), "%Y-%m-%dT%H:%M:%S.%fZ")
        return True
    except ValueError:
        return False


def convert_to_epoch(input):
    """Converts the time to epoch format."""
    date_time_obj = time.strptime(str(input), "%Y-%m-%dT%H:%M:%S.%fZ")
    epoch = calendar.timegm(date_time_obj)
    return epoch


def format_proxy_uri(proxy_dict):
    """
    Function to get proxy uri in format of.

    <protocol>://<user_name>:<password>@<proxy_server_ip>:<proxy_port>

    :param proxy_dict: dict, Dictionary containing proxy information

    :return: proxy_uri: str, proxy uri in standard format
    """
    uname = requests.compat.quote_plus(proxy_dict.get("proxy_username", ""))
    passwd = requests.compat.quote_plus(proxy_dict.get("proxy_password", ""))
    protocol = proxy_dict.get("proxy_type")
    proxy_url = proxy_dict.get("proxy_url")
    proxy_port = proxy_dict.get("proxy_port")
    proxy_uri = "%s://%s:%s@%s:%s" % (protocol, uname, passwd, proxy_url, proxy_port)

    return proxy_uri


def verify_ssl(connector):
    """
    A function that checks if a CA certificate is being used and returns the verification method accordingly.

    :param connector: dict, Dictionary containing connector information
    :return: str, The verification method based on the CA certificate usage
    """
    use_ca_cert = connector.get("use_ca_cert")
    verify_ssl = VERIFY_SSL
    if is_true(use_ca_cert):
        cert_file_loc = CERT_FILE_LOC.format(
            cert_name=connector.get("copy_account_name").strip()
        )
        verify_ssl = cert_file_loc
    return verify_ssl


def validate_global_account(helper, global_account, error_msg_prefix):
    """
    Function to validate the 'global_account' parameter, configured by the user in the Configuration settings.

    :param helper: Add-on Builder helper object for logging
    :param global_account: Global account dictionary containing information configured in the Configuration page
    :param error_msg_prefix: Prefix for error messages
    """
    if not global_account:
        msg = "global account not found. Please add the valid global account."
        helper.log_error(error_msg_prefix + msg)
        raise ValueError(msg)


def validate_start_date(helper, start_date, error_msg_prefix):
    """
    Function to validate the 'start_date' parameter, configured by the user in the Configuration settings.

    :param helper: Add-on Builder helper object for logging
    :param start_date: Start date string
    :param error_msg_prefix: Prefix for error messages
    """
    current_utc = calendar.timegm(datetime.datetime.utcnow().timetuple())
    if start_date:
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", start_date):
            msg = 'start date should be in "YYYY-MM-DDThh:mm:ssZ" format.'
            helper.log_error(error_msg_prefix + msg)
            raise ValueError(msg)

        time_pattern = "%Y-%m-%dT%H:%M:%SZ"
        start_date = calendar.timegm(time.strptime(start_date, time_pattern))

        if start_date < 0:
            msg = 'start date can not be lesser than "1970-01-01T00:00:00Z".'
            helper.log_error(error_msg_prefix + msg)
            raise ValueError(msg)

        if start_date > current_utc:
            msg = "start date can not be greater than current UTC."
            helper.log_error(error_msg_prefix + msg)
            raise ValueError(msg)
