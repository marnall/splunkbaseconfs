"""Utility methods for Cisco Catalyst AddOn."""

import import_declare_test  # noqa: F401

import base64
import calendar
import datetime
import json
import os
import time
import traceback
import urllib.parse

import cisco_catalyst_exceptions as cce
import consts

import requests
from solnlib import conf_manager
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi
from splunktaucclib.rest_handler.endpoint import DataInputModel
from splunktaucclib.rest_handler.endpoint.validator import Validator

DATA_COLLECTION_TERMINATION = "Cisco Catalyst Cyber Vision Error: failed to complete data collection and terminated."
DATA_COLLECTION_ERROR = (
    "Cisco Catalyst Cyber Vision Error: while collecting {} data: {}"
)


def get_account_config(session_key: str, conf_file, logger) -> conf_manager.ConfFile:
    """
    Return API access token for a specific account_name.

    :param session_key: session key for particular modular input.
    :param account_name: account name configured in the addon.
    """
    account_config_file = {}
    try:
        logger.debug("Getting conf file '%s' information.", conf_file)
        cfm = conf_manager.ConfManager(
            session_key,
            consts.APP_NAME,
            realm=f"__REST_CREDENTIAL__#{consts.APP_NAME}#configs/conf-{conf_file}",
        )
        account_config_file = cfm.get_conf(conf_file)
        logger.debug("Successfully received conf file '%s' information.", conf_file)

    except Exception:
        logger.exception(f"Error occurred while reading {conf_file}.conf.")

    return account_config_file


def get_checkpoint(
    session_key, checkpoint_key, logger, collection_name=consts.COLLECTION_NAME
):
    """Get KV Store checkpoint for the provided key."""
    logger.debug("Getting the checkpoint for key: %s", checkpoint_key)
    checkpoint_value = {}
    try:
        checkpoint_object = checkpointer.KVStoreCheckpointer(
            collection_name, session_key, consts.APP_NAME
        )
        checkpoint_value = checkpoint_object.get(checkpoint_key)
        logger.debug(
            "Successfully retrieved the checkpoint value for key: {}, value: {}".format(
                checkpoint_key, checkpoint_value
            )
        )
    except Exception as e:
        logger.error(
            "Error occured while getting the KV checkpoint value for the key: {}:{}".format(
                checkpoint_key, e
            )
        )

    return checkpoint_value


def update_checkpoint(
    session_key,
    checkpoint_key,
    checkpoint_value,
    logger,
    collection_name=consts.COLLECTION_NAME,
):
    """Update the KV Store checkpoint with the key value provided."""
    logger.debug("Updating checkpoint for key %s.", checkpoint_key)
    try:
        checkpoint_object = checkpointer.KVStoreCheckpointer(
            collection_name, session_key, consts.APP_NAME
        )
        checkpoint_object.update(checkpoint_key, checkpoint_value)
        logger.debug(
            "Checkpoint updated successfully for key: {}, value: {}.".format(
                checkpoint_key, checkpoint_value
            )
        )
    except Exception as e:
        logger.error(
            "Error occured while updating the kv checkpoint for the key: {}:{}".format(
                checkpoint_key, e
            )
        )
        raise e


def is_different(logger, state, item):
    """Check if the data returned from the API is different than the checkpointed values."""
    if not isinstance(state, dict):
        logger.debug("is_different. The state is not a dictionary.")
        return True
    if not isinstance(item, dict):
        logger.debug("is_different. The item is not a dictionary.")
        return True
    keys = set(state.keys())
    keys = keys.union(set(item.keys()))
    properties = list(keys)
    for property_ in properties:
        if state.get(property_) != item.get(property_):
            logger.debug(
                "is_different. The state and item have different values for property '{0}', values are {1} and {2}.".format(  # noqa: E501
                    property_,
                    state.get(property_),
                    item.get(property_),
                )
            )
            return True
    return False


def get_sslconfig(session_key, logger):
    """Get the verify_ssl flag or ca_cert file to be used for network calls."""
    app = consts.APP_NAME
    conf_name = "ta_cisco_catalyst_settings"
    session_key = urllib.parse.unquote(session_key.encode("ascii").decode("ascii"))
    session_key = session_key.encode().decode("utf-8")
    try:
        # Default value will be used for ca_certs_path if there is any error
        ssl_config = True
        ca_certs_path = ""

        cfm = conf_manager.ConfManager(
            session_key,
            app,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(app, conf_name),
        )
        stanza = cfm.get_conf(conf_name, refresh=True).get("additional_parameters")
        verify_ssl = is_true((stanza.get("verify_ssl") or "").strip().upper())
        ca_certs_path = (stanza.get("ca_certs_path") or "").strip()

    except Exception:
        msg = f"Error while fetching ca_certs_path from '{conf_name}' conf. Traceback: {traceback.format_exc()}"
        logger.error(msg)

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


def get_verify_ssl(session_key, logger):
    """Get the verify_ssl flag to be used for network calls."""
    app = consts.APP_NAME
    conf_name = "ta_cisco_catalyst_settings"
    session_key = urllib.parse.unquote(session_key.encode("ascii").decode("ascii"))
    session_key = session_key.encode().decode("utf-8")
    try:
        verify_ssl = True
        cfm = conf_manager.ConfManager(
            session_key,
            app,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(app, conf_name),
        )
        stanza = cfm.get_conf(conf_name, refresh=True).get("additional_parameters")
        verify_ssl = is_true((stanza.get("verify_ssl") or "").strip().upper())

    except Exception:
        msg = f"Error while fetching verify_ssl from '{conf_name}' conf. Traceback: {traceback.format_exc()}"
        logger.error(msg)

    if not verify_ssl:
        logger.debug("SSL Verification is set to False.")
        verify_ssl = False
    else:
        logger.debug("SSL Verification is set to True.")
        verify_ssl = True

    return verify_ssl


def is_true(val):
    """
    Check truthy value of the given parameter.

    :param val: Parameter of which truthy value is to be checkeds

    :return: True / False
    """
    value = str(val).strip().upper()
    if value in ("1", "TRUE", "T", "Y", "YES"):
        return True
    return False


class CyberVisionModel(DataInputModel):
    """CyberVision validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        # Add hidden fields to avoid insertion error
        data["page_size"] = data.get("page_size", "")
        super(CyberVisionModel, self).validate(name, data, existing)


class IntervalValidator(Validator):
    """Class to validate the interval."""

    def validate(self, value, data):
        """Validate the interval value."""
        interval = data.get("interval")
        try:
            interval = int(interval)
            if interval < 60:
                raise cce.CyberVisionInvalidInterval
            return True
        except cce.CyberVisionInvalidInterval:
            self.put_msg("Interval should be greater than or equal to 60 seconds.")
            return False
        except Exception:
            self.put_msg("Interval should be greater than or equal to 60 seconds.")
            return False


class ValidateStartDate(Validator):
    """Class to validate start date field."""

    def __init__(self, *args, **kwargs):
        """:param validator: user-defined validating function."""
        super(ValidateStartDate, self).__init__()
        self.my_app = consts.APP_NAME

    def validate(self, value, data):
        """Validate the start date field."""
        start_date = data["start_date"]
        try:
            formatted_start_date = datetime.datetime.strptime(
                start_date, "%Y-%m-%dT%H:%M:%SZ"
            )
        except ValueError:
            msg = 'Please enter correct UTC date of format "YYYY-MM-DDTHH:MM:SSZ".'
            self.put_msg(msg)
            return False
        if formatted_start_date >= datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None):
            msg = "Please enter start date less than current date time."
            self.put_msg(msg)
            return False
        else:
            return True


def get_proxy_uri(username, password, protocol, proxy_url, proxy_port):
    """Get proxy uri in format of <protocol>://<user_name>:<password>@<proxy_server_ip>:<proxy_port>."""
    if username and password:
        username = requests.compat.quote_plus(username)
        password = requests.compat.quote_plus(password)
        proxy_uri = "%s://%s:%s@%s:%s" % (
            protocol,
            username,
            password,
            proxy_url,
            proxy_port,
        )
    else:
        proxy_uri = "%s://%s:%s" % (protocol, proxy_url, proxy_port)
    return proxy_uri


def get_cybervision_startdate(input, config_details, checkpoint_value, logger):
    """Initialize start date for particular sourcetype of particular input."""
    start_date = input.get("start_date")
    if start_date:
        time_pattern = "%Y-%m-%dT%H:%M:%SZ"
        try:
            start_date = calendar.timegm(time.strptime(start_date, time_pattern))
        except Exception:
            err_msg = (
                "CyberVision Error: Start date is not in format %Y-%m-%dT%H:%M:%SZ"
            )
            logger.error(err_msg)
            raise cce.CyberVisionInvalidStartDate(err_msg)
        start_date = int(start_date * 1000)
    else:
        start_date = config_details.get("end_date") - (
            7 * 86400 * 1000
        )  # 7 Days in Milliseconds

    start_date = checkpoint_value if checkpoint_value else start_date
    return start_date


def get_sdwan_hours(checkpoint_value):
    """Initialize start date for particular sourcetype of particular input."""
    last_n_hours = 1
    if checkpoint_value:
        checkpoint_value = datetime.datetime.fromtimestamp(
            checkpoint_value / 1000.0
        ) - datetime.timedelta(minutes=consts.SDWAN_CHECKPOINT_WINDOW_IN_MINUTES)
        cur_time = datetime.datetime.now()
        diff_in_hours = (cur_time - checkpoint_value).total_seconds() / 3600

        if diff_in_hours < 24:
            last_n_hours = int(diff_in_hours)

    return last_n_hours


def get_cybervision_checkpoint_name(config_details, sourcetype, endpoint):
    """Get checkpoint name."""
    stanza_name = config_details.get("stanza")
    sourcetype = sourcetype.split(":")[-1]
    endpoint = endpoint.split("/")[-1]

    return stanza_name + "_" + sourcetype + "_" + endpoint


def get_sdwan_checkpoint_name(config_details, health_type):
    """
    Get checkpoint name for SDWAN.

    :param config_details: Basic configuration details
    :param health_type: Health type
    :return: Checkpoint name
    """
    stanza_name = "_".join(config_details.get("input_stanza_name").split("://"))

    return "_".join([stanza_name, health_type])


def get_ise_checkpoint_name(config_details, input_type):
    """
    Get checkpoint name for ISE.

    :param config_details: Basic configuration details
    :param input_type: Input type
    :return: Checkpoint name
    """
    stanza_name = "_".join(config_details.get("input_stanza_name").split("://"))

    return "_".join([stanza_name, input_type])


def cybervision_request_get(endpoint, config_details, params=None):
    """Make request to CyberVision.

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
    response = requests.get(
        url,
        params=params,
        headers=header_data,
        verify=verify_ssl,
        proxies=proxy_settings,
    )
    response.raise_for_status()
    data = json.loads(response.text)
    return data


def cybervision_ingest_in_splunk(
    input, ew, records, sourcetype, additional_fields, source=None
):
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
        if "host" in additional_fields:
            host = additional_fields["host"]
        if index_time:
            if not is_time_format(index_time):
                index_time = int(index_time) / 1000.0
            else:
                index_time = convert_to_epoch(index_time)
        else:
            index_time = time.time()

        event = smi.Event(
            time=index_time,
            data=json.dumps(record, ensure_ascii=False),
            host=host,
            index=input.get("index"),
            source=source,
            sourcetype=sourcetype,
            done=True,
            unbroken=True,
        )
        ew.write_event(event)


def is_time_format(input):
    """Check whether the given input is in time format or not."""
    try:
        time.strptime(str(input), "%Y-%m-%dT%H:%M:%S.%fZ")
        return True
    except ValueError:
        return False


def convert_to_epoch(input):
    """Convert the time to epoch format."""
    date_time_obj = time.strptime(str(input), "%Y-%m-%dT%H:%M:%S.%fZ")
    epoch = calendar.timegm(date_time_obj)
    return epoch


def save_cert_file(custom_certificate, cert_file_loc, logger):
    """Save the certificate file."""
    logger.info("Custom CA Certificate has been provided.")
    cert_dir_loc = os.path.dirname(cert_file_loc)
    if not os.path.exists(cert_dir_loc):
        os.makedirs(cert_dir_loc)
        logger.info("custom_certs directory has been created.")
    with open(cert_file_loc, "w") as f:
        f.write(custom_certificate)
    verify_ssl = cert_file_loc
    logger.info("Custom CA Certificate has been copied at {}.".format(cert_file_loc))
    return verify_ssl


def delete_cert_file(use_ca_cert, custom_certificate, cert_file_loc, logger):
    """Delete the certificate file.

    :param use_ca_cert (bool): account uses CA Cert or not
    :param custom_certificate (string): custom certificate
    :param cert_file_loc (string): location of certificate file
    :param logger (object): logger object
    """
    try:
        if (
            is_true(use_ca_cert)
            and custom_certificate
            and os.path.exists(cert_file_loc)
        ):
            os.remove(cert_file_loc)
            logger.info(
                "Custom CA Certificate has been deleted {}.".format(cert_file_loc)
            )
    except Exception as e:
        logger.error(
            f"Exception occurred while deleting custom certificate. Message - {e}"
        )


class Config:
    """Handle SSL and Proxy Configuration."""

    def __init__(self, session_key, account_conf_info, logger):
        """
        Initialize the Config object.

        :param session_key (str): session key
        :param account_conf_info (dict): account configuration information
        :param logger (object): logger object
        """
        self.session_key = session_key
        self.account_conf_info = account_conf_info
        self.logger = logger

    def get_verify_ssl_cert(self):
        """Get verify ssl settings."""
        use_ca_cert = self.account_conf_info.get("use_ca_cert")
        verify_ssl = True
        if is_true(use_ca_cert):
            verify_ssl = consts.ISE_CERT_FILE_LOC.format(
                cert_name=self.account_conf_info.get("copy_account_name").strip()
            )
        else:
            verify_ssl = get_verify_ssl(self.session_key, self.logger)
        return verify_ssl

    def get_proxy_settings(self):
        """Get proxy settings."""
        proxy_settings = None
        if is_true(self.account_conf_info.get("enable_proxy")):
            proxy_username = self.account_conf_info.get("proxy_username", "")
            proxy_password = self.account_conf_info.get("proxy_password", "")
            proxy_type = self.account_conf_info.get("proxy_type")
            proxy_url = self.account_conf_info.get("proxy_url")
            proxy_port = self.account_conf_info.get("proxy_port")
            proxy_uri = get_proxy_uri(
                proxy_username, proxy_password, proxy_type, proxy_url, proxy_port
            )
            proxy_settings = {"http": proxy_uri, "https": proxy_uri}
        return proxy_settings


def make_headers(username, password):
    """Encode username:password for Basic Auth.

    :param username: username for Auth.
    :param password: password for Auth.
    :return encoded username:password
    """
    if password is None:
        password = ""
    user_pass = ":".join([username, password])
    auth_header = base64.b64encode(user_pass.encode("utf-8")).decode("utf-8")
    headers = {"Authorization": f"Basic {auth_header}", "accept": "application/json"}
    return headers


def try_parse_json(value):
    """Parse data to json."""
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value


def clean_row(row):
    """Format and clean raw."""
    cleaned = {}
    for key, value in row.items():
        if key is None:
            continue
        clean_key = str(key).strip().strip('"')
        if isinstance(value, str):
            value = value.strip().replace('\\"', '"')
            value = try_parse_json(value)
        cleaned[clean_key] = value
    return cleaned
