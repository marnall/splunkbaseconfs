import logging
import logging.handlers
import os
import sys

import splunk
from splunklib.searchcommands import StreamingCommand

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))


def setup_logging():
    """
    This function sets up logging for the application. It creates a logger instance, configures it to write logs to a file,
    and sets up the logging format.

    Parameters:
    None

    Returns:
    logger (logging.Logger): The configured logger instance.
    """
    logger = logging.getLogger("splunk.foo")
    SPLUNK_HOME = os.environ["SPLUNK_HOME"]

    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log.cfg")
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log-local.cfg")
    LOGGING_STANZA_NAME = "python"
    LOGGING_FILE_NAME = "ipqualityscore.log"
    BASE_LOG_PATH = os.path.join("var", "log", "splunk")
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"

    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode="a"
    )
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)

    splunk.setupSplunkLogger(
        logger,
        LOGGING_DEFAULT_CONFIG_FILE,
        LOGGING_LOCAL_CONFIG_FILE,
        LOGGING_STANZA_NAME,
    )

    return logger


class BaseIPQualityScoreCommand(StreamingCommand):
    """
    Base class for IP Quality Score commands, used to process and validate
    records from Splunk streams based on a specified field.
    """

    def get_credentials(self):
        """
        Retrieves the credentials stored in Splunk for IPQualityScore access.

        Returns:
            dict | None: A dictionary containing the 'username' and 'password'
            if found, otherwise None.
        """
        storage_passwords = self.service.storage_passwords
        for credential in storage_passwords:
            if credential.content.get("realm") == "ipqualityscore_realm":
                return {
                    "username": credential.content.get("username"),
                    "password": credential.content.get("clear_password"),
                }
        return None

    def process_records(self, records, logger):
        """
        Processes records to segregate those containing the specified field
        from those that do not.

        Args:
            records (list[dict]): List of event records to process.
            logger: Logger object to log error messages.

        Returns:
            tuple[list[dict], list[dict]]: A tuple containing two lists:
            one with valid records (having the required field) and another
            with records that are missing the required field.
        """
        correct_records = []
        incorrect_records = []
        for record in records:
            if record.get(self.field):
                correct_records.append(record)
            else:
                incorrect_records.append(record)

        if len(incorrect_records) > 0:
            logger.error(
                f"{self.field} field missing from {len(incorrect_records)} events. They will be ignored."
            )

        return correct_records, incorrect_records

    def handle_results(self, correct_records, results_dict, client):
        """
        Handles results by adding API call information to records based on the
        detection results provided by the IPQualityScore API.

        Args:
            correct_records (list[dict]): List of records that contain the required field.
            results_dict (dict): Dictionary of detection results keyed by the field value.
            client: The IPQualityScore client instance used to interact with the API.

        Yields:
            dict: Records enriched with detection results and status.
        """
        for record in correct_records:
            detection_result = results_dict.get(record[self.field])

            if detection_result is not None:
                for key, val in detection_result.items():
                    new_key = client.get_prefix() + "_" + key
                    self.add_field(record, new_key, val)
                if "from_db_file" in detection_result:
                    self.add_field(
                        record, f"{client.get_prefix()}_status", "data fetched from db file"
                    )
                else:
                    self.add_field(
                        record, f"{client.get_prefix()}_status", "api call success"
                    )
            else:
                self.add_field(
                    record, f"{client.get_prefix()}_status", "api call failed"
                )

            yield record
