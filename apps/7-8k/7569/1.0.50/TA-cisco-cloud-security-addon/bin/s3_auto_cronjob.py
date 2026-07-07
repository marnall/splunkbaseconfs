from enum import Enum
import sys
import os
import import_declare_test
import logging
from common import Common
from splunklib.modularinput import Script, Scheme, Argument
from splunklib.modularinput.input_definition import InputDefinition
from logging.handlers import RotatingFileHandler
from utils import S3Utility, make_splunk_request, get_conf_stanza_details
from solnlib import conf_manager

def get_logger(log_name, log_level=logging.INFO):
    log_file = os.path.join(Common().log_path, f"{log_name}.log")
    logger = logging.getLogger(log_name)

    handler_exists = any(
        [True for item in logger.handlers if item.baseFilename == log_file]
    )

    if not handler_exists:
        file_handler = RotatingFileHandler(
            log_file, mode="a", maxBytes=25000000, backupCount=5
        )
        format_string = (
            "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s file=%(filename)s:%("
            "funcName)s:%(lineno)d | %(message)s "
        )
        formatter = logging.Formatter(format_string)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(log_level)
        logger.propagate = False

    return logger


logger = get_logger(
    f"{import_declare_test.ta_name}_{os.path.basename(__file__).split('.')[0]}"
)


class Handlers(Enum):
    ACCOUNT = "auto_rotate_handler"
    EVENT_LOG = "s3_auto_log_discovery_handler"


class S3AutoCronJob(Script):
    def __init__(self):
        super().__init__()
        self.logger = logger
        self._session_key: str = None
        self._ta_name = import_declare_test.ta_name
        self._aws_account_conf_name = "ta_cisco_cloud_security_addon_aws_account"
        self._aws_account_stanza = None

    def get_scheme(self):
        scheme = Scheme("Cisco Secure Access Add-on for Splunk: S3 auto cron job")
        scheme.description = "This script schedules and triggers S3 auto cron jobs."
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.add_argument(
            Argument(
                name="handler",
                title="Handler",
                description="Specify the handler to use for processing the input.",
                required_on_create=True,
                required_on_edit=False,
            )
        )
        return scheme

    def stream_events(self, inputs: InputDefinition, ew):
        """
        Main entry point for the script. Fetches accounts and performs key rotation if needed.
        """
        try:
            logger.info(
                f"Entry point of the script with inputs: {inputs}, event writer: {ew}"
            )

            self._session_key = inputs.metadata.get("session_key")
            input_data = list(inputs.inputs.items())
            if not input_data:
                logging.warning("No inputs found for stream_events.")
                return
            input_name = input_data[0][0].split("://")[-1]
            if not input_name:
                logging.warning(f"No event_name extracted from input_name '{input_name}'. Skipping make_splunk_request.")
                return
            input_fields = input_data[0][1]
            handler = Handlers[input_fields.get("handler")]
            
            if handler.value == "s3_auto_log_discovery_handler":
                data = {
                    "event_name": input_name
                }
                try:
                    self._call_auto_rotate_or_log_handler(handler, data)
                except Exception as e:
                    raise e
            elif handler.value == "auto_rotate_handler":
                # For account rotation, input_name is the AWS account name
                payload = {"name": input_name}
                
                try:
                    # Get AWS account configuration
                    self._aws_account_stanza = get_conf_stanza_details(
                        self._session_key, 
                        conf_file=self._aws_account_conf_name, 
                        stanza_name=input_name
                    )
                    access_key_id, secret_access_key, region = self._get_secure_credentials()

                    try:
                        # Validate AWS credentials
                        s3_util = S3Utility(self._session_key)
                        s3_util.validate_keys(region, access_key_id, secret_access_key)
                    except Exception as e:
                        # If validation fails, call auto rotate handler
                        if "Invalid AWS access key id or secret access key." in str(e):
                            logger.info(f"Auto rotate handler called for account {input_name} due to invalid credentials.")
                            self._call_auto_rotate_or_log_handler(handler, payload)
                            logger.info(f"Auto rotation was completed for the AWS account: {input_name}.")
                        else:
                            raise e
                except Exception as e:
                    logger.error(f"Error in stream_events: {e}")
                    raise e
            else:
                logger.warning(f"Unknown handler type: {handler.value}")
                
        except Exception as e:
            logger.error(f"Unhandled exception in stream_events: {e}", exc_info=True)
            raise e

    def _call_auto_rotate_or_log_handler(self, handler, payload):
        """
        Calls the handler using make_splunk_request only once.
        """
        try:
            make_splunk_request(
                endpoint=handler.value,
                method="POST",
                addon_namespace=True,
                session_key=self._session_key,
                data=payload,
            )
        except Exception as e:
            logger.error(f"Error while calling handler: {e}")
            raise e

    def _get_secure_credentials(self):
        """
        Retrieves secure credentials for the specified AWS account.

        Returns:
            tuple: (access_key_id, secret_access_key, region)
        """
        try:
            account_fields = self._aws_account_stanza
            return (
                account_fields.get("access_key_id"),
                account_fields.get("secret_access_key"),
                account_fields.get("region"),
            )
        except Exception as e:
            logger.error(f"Failed to retrieve secure credentials: {e}")
            raise


if __name__ == "__main__":
    logger.info(f"S3 Auto Cron Job script started: {sys.argv}")
    exit_code = S3AutoCronJob().run(sys.argv)
    logger.info("S3 Auto Cron Job script finished")
    sys.exit(exit_code)