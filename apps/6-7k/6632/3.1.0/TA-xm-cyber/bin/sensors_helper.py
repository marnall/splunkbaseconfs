"""Helper module for collecting and processing sensor data from XM Cyber."""
import import_declare_test  # noqa: F401
from xmcyber_collector import XMCyberCollector
from import_declare_test import ta_prefix
from log_helper import setup_logging
from xmcyber_utils import extract_input_context, validate_oauth_authentication
from xmcyber_constants import AUTH_ERROR_MESSAGE
import traceback

logger = setup_logging(f"{ta_prefix}_sensors")


def validate_input(definition):
    """Validate the input parameters for the modular input.

    Returns:
        bool: valueError if not valid.
    """
    validate_oauth_authentication(definition, "Sensors", logger)


def stream_events(inputs, event_writer):
    """
    Streams events from the sensors endpoint.

    Args
        inputs: A list of inputs from the modular input.
        event_writer: An object with methods to write events and log messages to Splunk.
    """
    # Extract common input parameters
    context = extract_input_context(inputs)
    account = context["account"]
    auth_type = context["auth_type"]
    normalized_input_name = context["normalized_input_name"]

    if auth_type == "basic":
        service_name = "Sensors"
        error_msg = AUTH_ERROR_MESSAGE.format(service_name=service_name, account=account)
        logger.error(f"input_name={normalized_input_name} {error_msg}")
    else:
        try:
            logger.info(f"input_name={normalized_input_name} Initializing sensors data collection.")
            sensors_collector = XMCyberCollector(inputs, event_writer)
            sensors_collector.collect_events(sensors_collector.xm_cyber_client.get_sensors)
            logger.info(f"input_name={normalized_input_name} Exiting sensors data collection.")
        except Exception as e:
            logger.error(
                f"input_name={normalized_input_name} Error in sensors data collection. "
                f"Error :{e} {traceback.format_exc()}"
            )
