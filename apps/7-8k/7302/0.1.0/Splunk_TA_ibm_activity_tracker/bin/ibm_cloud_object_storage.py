# ibm_cloud_object_storage.py
# standard
import datetime
import json
import logging
import os
import sys

# Splunk
import import_declare_test  # noqa: F401
from solnlib import conf_manager, log
from splunklib import modularinput as smi

# Third-party
import boto3

ADDON_NAME = "Splunk_TA_ibm_activity_tracker"
ADDON_INPUT_NAME = "ibm_cloud_object_storage"
SOURCETYPE = "ibm_activity_tracker"


def _logger_for_input(input_name: str) -> log:
    """
    Returns a logger
    Args:
        input_name: String representing the input name

    Returns: Solnlib logger for specified addon input

    """
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def _get_account(session_key: str, account_name: str) -> dict:
    """
    Gets account details from addon configuration file.
    Args:
        session_key (str): A string representing the session key.
        account_name (str): A string representing the account name.

    Returns:
        account (dict): Dictionary representing the account configuration provided via UI: credentials and endpoint_url.
    """
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{ADDON_NAME.lower()}_account",
    )
    account_conf_file = cfm.get_conf(f"{ADDON_NAME.lower()}_account")
    account = account_conf_file.get(account_name)
    return account


def _get_s3_resource(account: dict):
    """
    Provides s3 resource for interacting with the S3 bucket.
    Args:
        account (dict): Dictionary representing the account configuration provided via UI: credentials and endpoint_url.

    Returns:
        s3 (ServiceResource): s3 resource for interacting with the S3 bucket.
    """
    return boto3.resource(
        service_name="s3",
        aws_access_key_id=account["access_key_id"],
        aws_secret_access_key=account["secret_access_key"],
        endpoint_url=account["endpoint_url"],
    )


def _process_s3_object(
    event_writer: smi.EventWriter,
    index: str,
    logger: logging.Logger,
    normalized_input_name: str,
    obj,
) -> None:
    """
    Process and ingest to specified Splunk index.
    Args:
        event_writer (smi.EventWriter): Writes events and error messages to Splunk from a modular input.
        logger (logging.Logger): Logger instance.
        normalized_input_name (str): String representing input name.
        index (str): String representing target Splunk index.
        obj (Object): S3 Object that contains raw events ["Body"] and s3 metadata associated with it.
    """
    with obj.get()["Body"] as stream:
        lines = stream.read().splitlines()
        count = 0
        for line_bytes in lines:
            try:
                _ingest_event(event_writer, index, line_bytes)
            except Exception as e:
                logger.exception(
                    "Exception occurred while ingesting events into HEC: %s", str(e)
                )
            count += 1
        log.events_ingested(logger, normalized_input_name, SOURCETYPE, count)


def _ingest_event(event_writer: smi.EventWriter, index: str, line_bytes: bytes) -> None:
    """
    Ingests events to specified Splunk index.
    Args:
        event_writer (smi.EventWriter): Writes events and error messages to Splunk from a modular input.
        index (str): String representing target Splunk index.
        line_bytes (bytes): Bytes being decoded and sent to Splunk index.
    """
    datastr = line_bytes.decode()
    dataobj = json.loads(datastr)
    cadfevent = dataobj["line"]
    event = smi.Event(
        data=cadfevent,
        index=index,
        sourcetype=SOURCETYPE,
    )
    event_writer.write_event(event)


def _save_check_point(
    inputs: smi.InputDefinition, stanza: str, state: str, logger: logging.Logger
) -> None:
    """
    Saves checkpoint to a file.
    Args:
        inputs (smi.InputDefinition):
        stanza (str): String representation of the checkpoint file name without extension.
        state (str): Current state of the checkpoint.
        logger (logging.Logger): logger instance

    """
    checkpoint_dir = inputs.metadata["checkpoint_dir"]
    checkpoint_file_path = os.path.join(checkpoint_dir, stanza + ".txt")
    try:
        with open(checkpoint_file_path, "w") as file:
            file.write(state)
    except IOError as e:
        logger.exception("Failed to save checkpoint to a file: %s", str(e))
        raise e
    return


def _get_check_point(
    inputs: smi.InputDefinition, stanza: str, logger: logging.Logger
) -> str:
    """
    Reads checkpoint from file or creates an empty file if it doesn't exist.
    Args:
        inputs (smi.InputDefinition):
        stanza (str): String representation of the checkpoint file name without extension.
        logger (logging.Logger): logger instance.

    Returns:
        state (str): State of the last saved checkpoint.
    """
    checkpoint_dir = inputs.metadata["checkpoint_dir"]
    checkpoint_file_path = os.path.join(checkpoint_dir, f"{stanza}.txt")
    # Set the temporary contents of the checkpoint file to an empty string
    state = ""
    try:
        if os.path.isfile(checkpoint_file_path):
            with open(checkpoint_file_path, "r") as file:
                state = file.read()
        else:
            with open(checkpoint_file_path, "w") as file:
                logger.warning("No checkpoint, creating empty file.")
    except IOError as e:
        logger.exception("I/O error(%s): %s", e.errno, e.strerror)
        raise e
    return state


class Input(smi.Script):
    """
    Input class processes all defined ActivityTracker inputs for modular input script.
    """

    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme(ADDON_INPUT_NAME)
        scheme.description = f"{ADDON_INPUT_NAME} input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        """
        Validates the input parameters for modular input script.

        Args:
            definition (smi.ValidationDefinition): The definition containing input parameters.

        Raises:
            ValueError: If the "since" parameter is missing or not a valid ISO 8601 timestamp.
        """
        try:
            state = definition.parameters.get("since")
            start_date = datetime.datetime.fromisoformat(state)
            today = datetime.datetime.now(tz=start_date.tzinfo)
        except Exception as e:
            raise ValueError(
                "Since value error. Please specify a valid ISO 8601 timestamp.", str(e)
            )
        if start_date > today:
            raise ValueError("Start date can't be greater than today")

    def stream_events(
        self, inputs: smi.InputDefinition, event_writer: smi.EventWriter
    ) -> None:
        """
        Process ingestion of data from all defined inputs.
        Args:
            inputs (smi.InputDefinition): inputs definition containg dict representation of inputs:
        inputs.inputs is a Python dictionary object like:
        {
          "{ADDON_INPUT_NAME}://<input_name>": {
            "account": "<account_name>",
            "disabled": "0",
            "host": "$decideOnStartup",
            "index": "<index_name>",
            "interval": "<interval_value>",
            "python.version": "python3",
          },
        }
            event_writer (smi.EventWriter):  Writes events and error messages to Splunk from a modular input.
        """
        for input_name, input_item in inputs.inputs.items():

            normalized_input_name = input_name.split("/")[-1]
            logger = _logger_for_input(normalized_input_name)
            try:
                session_key = self._input_definition.metadata["session_key"]
                self._configure_logger(logger, session_key)
                log.modular_input_start(logger, normalized_input_name)
                account = _get_account(session_key, input_item.get("account"))
                state = _get_check_point(
                    inputs, normalized_input_name, logger
                ) or input_item.get("since")
                state = self._process_log_files(
                    account,
                    event_writer,
                    input_item,
                    logger,
                    normalized_input_name,
                    state,
                )
                _save_check_point(inputs, normalized_input_name, state, logger)
                log.modular_input_end(logger, normalized_input_name)
            except Exception as e:
                logger.exception(
                    "Exception raised while ingesting data for %s: %s.",
                    ADDON_INPUT_NAME,
                    str(e),
                )

    @staticmethod
    def _configure_logger(logger: logging.Logger, session_key: str) -> None:
        """
        Configures logger
        Args:
            logger (logging.Logger): Logger to be configured
            session_key (str): Splunk session key

        """
        log_level = conf_manager.get_log_level(
            logger=logger,
            session_key=session_key,
            app_name=ADDON_NAME,
            conf_name=f"{ADDON_NAME.lower()}_settings",
        )
        logger.setLevel(log_level)

    @staticmethod
    def _process_log_files(
        account: dict,
        event_writer: smi.EventWriter,
        input_item: dict,
        logger: logging.Logger,
        normalized_input_name: str,
        state: str,
    ) -> str:
        """
        Fetches log files from COS bucket and ingests to Splunk.
        Args:
            account (dict): A dict representation of  account configuration.
            event_writer (smi.EventWriter): Writes events and error messages to Splunk from a modular input.
            input_item (dict): A dict representation of s3 object
            logger (logging.Logger): Logger instance
            normalized_input_name (str): String representation of input name
            state (str): String representing current checkpoint

        Returns:
            state (str): String representation of updated checkpoint.
        """
        s3 = _get_s3_resource(account)
        since = datetime.datetime.fromisoformat(state)
        last = since
        bucket = s3.Bucket(input_item.get("bucket"))  # type: ignore
        for object_meta in bucket.objects.all():
            if object_meta.key.endswith(".log") and since < object_meta.last_modified:
                obj = s3.Object(input_item.get("bucket"), object_meta.key)  # type: ignore
                if obj.content_length != 0:
                    _process_s3_object(
                        event_writer,
                        input_item.get("index"),  # type: ignore
                        logger,
                        normalized_input_name,
                        obj,
                    )
                if last < object_meta.last_modified:
                    last = object_meta.last_modified
        return last.isoformat()


if __name__ == "__main__":
    exit_code = Input().run(sys.argv)
    sys.exit(exit_code)
