import datetime
import json
import logging
import re
from typing import Any, Dict, List, Optional

import pytz
import requests
from solnlib import conf_manager, log

# import dateparser

VALIDATE_INPUT_LOWER_VERSION = "9.1.0"
ADDON_NAME = "TA_cyberint_argos"
ADDON_PATH = "TA-cyberint-argos"
ALERTS_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
FIELD_DELIMITER = '|'


def logger_for_input(input_name: str) -> logging.Logger:
    """
    Get the logger for the given input name.

    Args:
        input_name (str): Input name.

    Returns:
        logging.Logger: The logger of the given input.
    """
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_account_api_key(session_key: str, account_name: str) -> str:
    """
    Get the API key for the given account name.

    Args:
        session_key (str): Session key.
        account_name (str): Account name to get the API key for.

    Returns:
        str: Cyberint Rest API key.
    """
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_PATH,
        realm=f"__REST_CREDENTIAL__#{ADDON_PATH}#configs/conf-ta_cyberint_argos_account",
    )
    account_conf_file = cfm.get_conf("ta_cyberint_argos_account")
    return account_conf_file.get(account_name).get("api_key")


def get_proxy_settings(session_key: str) -> str:
    """
    Get the proxy settings.

    Args:
        session_key (str): Session key.

    Returns:
        str: Proxy settings.
    """
    PROXY_DISABLE = "0"
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_PATH,
        realm=f"__REST_CREDENTIAL__#{ADDON_PATH}#configs/conf-ta_cyberint_argos_settings",
    )
    settings_conf_file = cfm.get_conf("ta_cyberint_argos_settings")
    proxy_stanza = settings_conf_file.get("proxy")
    if proxy_stanza.get("proxy_enabled") == PROXY_DISABLE:
        return None
    return create_proxy_uri_dict(proxy_stanza)

def get_version(session_key: str) -> str:
    """
    Get the application version.

    Args:
        session_key (str): Session key.

    Returns:
        str: Version.
    """
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_PATH,
        realm=f"__REST_CREDENTIAL__#{ADDON_PATH}#configs/conf-app",
    )
    app_conf_file = cfm.get_conf("app")
    proxy_stanza = app_conf_file.get("id")
    return proxy_stanza.get("version")

def create_proxy_uri_dict(proxy_dict):
    """
    This is utility method which returns proxy dict with composed uri in a format which requests package accepts.

    :param proxy_dict: dict containing proxy details
    :return proxies: proxy dict (for ex.: {'http': '<uri>', https: '<uri>'} and empty
                                 dict object is returned when proxy is disabled)
    """
    proxies = {}
    proxy_status = proxy_dict.get("proxy_enabled") or "0"
    if proxy_status.lower() in ["true", "1", "yes"]:
        uri = proxy_dict["proxy_url"]
        if proxy_dict.get("proxy_port"):
            uri = "{}:{}".format(uri, proxy_dict["proxy_port"])
        if proxy_dict.get("proxy_username") and proxy_dict.get("proxy_password"):
            uri = "{}://{}:{}@{}/".format(
                proxy_dict["proxy_type"],
                requests.compat.quote_plus(str(proxy_dict["proxy_username"])),
                requests.compat.quote_plus(str(proxy_dict["proxy_password"])),
                uri,
            )
        else:
            uri = "{}://{}".format(proxy_dict["proxy_type"], uri)
        proxies = {"http": uri, "https": uri}
    return proxies


def remove_empty_elements(value: Any) -> Any:
    """
    Remove empty elements from values.

    Args:
        value (Any): Value the remove empty elements.

    Returns:
        Any: The value without empty elements.
    """
    def empty(x: Any) -> bool:
        return x is None or x == {} or x == []

    if isinstance(value, dict):
        return {
            k: v for k, v in ((k, remove_empty_elements(v))
                              for k, v in value.items()) if not empty(v)
        }
    if isinstance(value, list):
        return [v for v in (remove_empty_elements(v) for v in value) if not empty(v)]
    return value


def convert_time_frame_to_utc(time_frame: str) -> str:
    """
    Convert a verbal time to ISO 8061 time.

    Args:
        time_frame (str): A verbal time.

    Returns:
        str: ISO 8061 time.
    """
    current_utc_time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

    conversion_dict = {
        "last_1h": current_utc_time - datetime.timedelta(hours=1),
        "last_24h": current_utc_time - datetime.timedelta(hours=24),
        "last_7d": current_utc_time - datetime.timedelta(days=7),
        "last_30d": current_utc_time - datetime.timedelta(days=30),
        "last_90d": current_utc_time - datetime.timedelta(days=90)
    }

    return conversion_dict.get(time_frame, current_utc_time).strftime(ALERTS_DATE_FORMAT)


def load_checkpoint(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Get data from checkpoint file.

    Args:
        file_path (str): The of the file.

    Returns:
        Optional[Dict[str, Any]]: Data from the checkpoint file.
    """
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logging.warning(f'Checkpoint file not found: {file_path}')
    except Exception as e:
        logging.error(f'Error reading checkpoint file: {file_path}. Reason: {e}')
    return None


def valid_date_in_checkpoint(checkpoint, input_start_time):
    """Check if the checkpoint contains a valid last_run and matches the input start time."""
    if (
        checkpoint
        and checkpoint.get('start_time') == input_start_time
        and is_valid_date(checkpoint.get('last_run'))
    ):
        return True
    return False


def get_last_run(checkpoint_filename: str, input_start_time: str, logger: logging.Logger) -> str:
    """
    Get the last request run time.

    Args:
        checkpoint_filename (str): A path for the saved last run file.
        input_start_time (str): The start time that configured in the input.
        logger (logging.Logger): Logger for logging.

    Returns:
        str: The last request run time.
    """
    checkpoint = load_checkpoint(checkpoint_filename)

    if valid_date_in_checkpoint(checkpoint, input_start_time):
        last_run_from_file = checkpoint.get('last_run')
        logger.info(f'Using last_run from checkpoint file: {last_run_from_file}')
        return last_run_from_file

    if input_start_time is not None:
        if is_valid_date(input_start_time):
            logger.info(f'Using provided input start_time: {input_start_time}')
            return input_start_time

        utc_time = convert_time_frame_to_utc(input_start_time)
        if utc_time:
            logger.info(f'Converted input start_time to UTC: {utc_time}')
            return utc_time
    else:
        logger.warning('Input start_time is None. Using current UTC time.')

    current_utc_time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc).strftime(ALERTS_DATE_FORMAT)
    logger.info(f'Using current UTC time as start_time: {current_utc_time}')
    return current_utc_time


def handle_update_last_run(last_run: str, alerts: list, logger: logging.Logger) -> str:
    """
    Handle the update of last request run.

    Args:
        last_run (str): The current 'last_run' argument.
        alerts (list): A list of fetched alerts.
        logger (logging.Logger): Logger for logging.

    Returns:
        str: The new last request run time.
    """
    last_run = datetime.datetime.strptime(last_run, ALERTS_DATE_FORMAT)

    for alert in alerts:
        update_date = datetime.datetime.strptime(alert['update_date'], ALERTS_DATE_FORMAT)

        if update_date > last_run:
            last_run = update_date
    if len(alerts) > 0:
        last_run += datetime.timedelta(seconds=1)

    last_run = datetime.datetime.strftime(
        last_run, ALERTS_DATE_FORMAT)

    logger.debug('last_run will update to %s', last_run)
    return last_run


def update_last_run(last_run: str, start_time: str, filename: str, logger: logging.Logger):
    """
    Update the last request run time.

    Args:
        last_run (str): Last request run time to update.
        start_time (str): The start time the user configure in the application input.
        filename (str): The filename to save the last request run time.
        logger (logging.Logger): Logger configuration for logging.
    """
    checkpoint_data = {
        'last_run': last_run,
        'start_time': start_time
    }

    try:
        with open(file=filename, mode='w') as f:
            json.dump(checkpoint_data, f)
        logger.info(f'Successfully updated checkpoint file: last_run to {last_run} and start_time to {start_time}')
    except Exception as e:
        logger.error(f'Failed to update checkpoint file. Reason: {e}')
        raise


def is_valid_date(str_date: str) -> bool:
    """
    Validate that a date string is correct.

    Args:
        str_date (str): A date to validate.

    Returns:
        bool: If the date is valid.
    """

    try:
        datetime.datetime.strptime(str_date, ALERTS_DATE_FORMAT)
        return True
    except ValueError:
        return False


def camel_to_snake(value: str) -> str:
    """
    Converts a camelCase string to snake_case.

    Args:
        value (str): The string to convert.

    Returns:
        str: The converted string.
    """
    value = value.replace(" ", "")
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def string_to_list_camel_to_snake(data: str):
    return [camel_to_snake(value) for value in data.split('|')] if data else None


def string_to_list(input_str: str) -> List[str]:
    """
    Convert a comma-separated string or None to a list.

    Args:
        input_str (str): Comma-separated string or None.

    Returns:
        list: List of strings obtained from the input string, or an empty list if input_str is None.
    """
    return [item.strip() for item in (input_str or "").split(",")] if input_str else None


def string_to_bool(input_str: str) -> bool:
    """
    Convert a '0' or '1' string to a boolean value.

    Args:
        input_str (str): A string containing '0' or '1'.

    Returns:
        bool: False if input_str is '0', True if input_str is '1'.
    """
    return bool(int(input_str))


def extract_environment_value(decode: str) -> str:
    """
    Extracts the environment value from the provided decode string.

    Parameters:
    - decode (str): The input string containing the environment information.

    Returns:
    - str: The extracted environment value. If not found, returns an empty string.
    """

    # Extract the JSON part from the string
    match = re.search(r'{.*}', decode)
    if match:
        json_str = match.group(0)
        json_obj = json.loads(json_str)

        # Extract the 'message' from the JSON object
        message = json_obj.get('message', '')

        # Extract the environment value from the message
        env_match = re.search(r"unrecognized environment: ([^\"]+)", message)
        if env_match:
            return env_match.group(1)

    return ""


def get_current_date() -> str:
    """
    Get the current date in string formated to ISO 8061.

    Returns:
        str: The current date.
    """
    return datetime.datetime.strftime(datetime.datetime.now(), ALERTS_DATE_FORMAT)


def is_lower_version(version: str, reference_version: str = VALIDATE_INPUT_LOWER_VERSION) -> bool:
    """
    Check if Splunk version is lower than the reference version.

    Args:
        version_str (str): Splunk current version (For example, 9.1.2).
        reference_version (str): Reference version (For example, 9.1.2). Default to 9.1.0.

    Returns:
        bool: True if the version is lower than the reference version.
    """
    version_tuple = tuple(map(int, version.split('.')))
    reference_tuple = tuple(map(int, reference_version.split('.')))

    return version_tuple < reference_tuple
