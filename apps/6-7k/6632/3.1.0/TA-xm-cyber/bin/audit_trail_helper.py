"""Helper module for collecting and processing audit trail data from XM Cyber."""
import import_declare_test  # noqa: F401
from xmcyber_collector import XMCyberCollector
from import_declare_test import ta_prefix
from log_helper import setup_logging
import traceback
from xmcyber_utils import extract_input_context, validate_oauth_authentication
from xmcyber_constants import AUTH_ERROR_MESSAGE

logger = setup_logging(f"{ta_prefix}_audit_trail")


def validate_input(definition):
    """Validate the input parameters for the modular input.

    Returns:
        bool: valueError if not valid.
    """
    validate_oauth_authentication(definition, "Audit Trail", logger)


def stream_events(inputs, event_writer):
    """
    Streams events from the Audit Trail endpoint.

    Args:
        inputs: A list of inputs from the modular input.
        event_writer: An object with methods to write events and log messages to Splunk.
    """
    # Extract common input parameters
    context = extract_input_context(inputs)
    account = context["account"]
    auth_type = context["auth_type"]
    normalized_input_name = context["normalized_input_name"]

    if auth_type == "basic":
        service_name = "Audit Trail"
        error_msg = AUTH_ERROR_MESSAGE.format(service_name=service_name, account=account)
        logger.error(f"input_name={normalized_input_name} {error_msg}")
    else:
        try:
            logger.info(f"input_name={normalized_input_name} Initializing audit trail data collection.")
            audit_collector = XMCyberCollector(inputs, event_writer)
            audit_collector.collect_events(audit_collector.xm_cyber_client.get_audit_trail)
            logger.info(f"input_name={normalized_input_name} Exiting audit trail data collection.")
        except Exception as e:
            logger.error(
                f"input_name={normalized_input_name} Error in audit trail data collection. "
                f"Error :{e} {traceback.format_exc()}"
            )
