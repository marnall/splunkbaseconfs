import sys # noqa: I001

import import_declare_test  # noqa
import requests
from CiscoSecurityCloud.exceptions import KVStoreTimeoutError
from CiscoSecurityCloud.sna.collect_events import collect_events
from CiscoSecurityCloud.sna.sna_api_client import SNAApiClient
from CiscoSecurityCloud.sna.utils import SNAConfig
from CiscoSecurityCloud.utils import create_and_configure_logger
from splunklib import modularinput as smi

LOGGER = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class SBGSNAInput(smi.Script):
    """A base class that extends :class:`smi.Script`
    for implementing modular input Secure Network Analytics.

    Methods ``get_scheme``, ``validate_input``,
    and ``stream_events`` for external validation.
    """
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        """The scheme defines the parameters understood by this modular input.

        :return: ``Scheme`` object representing the parameters for this modular input.
        """
        scheme = smi.Scheme("sbg_sna_input")
        scheme.description = "Secure Network Analytics"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name",
                required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "ip_address",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "domain_id",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "username",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "loglevel",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "alarms",
                title="Alarms",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "include_risk_events",
                title="Risk Events",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition):
        """Handles external validation for modular input.

        If this function does not throw an exception, the validation is assumed
        to succeed. Otherwise, any errors thrown will be turned into a string and
        logged back to Splunk.

        :param definition: The parameters for the proposed input passed by splunk.
        """
        input_name = definition.metadata["name"]
        session_key = definition.metadata["session_key"]
        input_item = definition.parameters

        config = SNAConfig.from_input_item(
            input_name, input_item, session_key
        )
        sna_api_session = SNAApiClient(config, input_name)

        try:
            if sna_api_session.login():
                LOGGER_STATUS.info(
                    f"instance={input_name}, "
                    "product=SNA, "
                    "filter_value=sbg_sna_input.py, "
                    "status=Connected,"
                )
            else:
                LOGGER_STATUS.info(
                    f"instance={input_name}, "
                    "error_type=Configuration, "
                    "product=SNA, "
                    "filter_value=sbg_sna_input.py, "
                    "status=Not Connected, "
                )
        except requests.exceptions.ConnectionError as ce:
            #  No connection established due to invalid Host IP
            LOGGER_ERROR.error(
                f"instance={input_name}, "
                f"error_type=Configuration, "
                f"error_code={type(ce).__name__}, "
                f"error_detail=Unable to process {input_name}, "
                f"traceback={ce}, "
                f"filter_value=sbg_sna_input.py, "
            )
            raise ValueError(
                "The provided API credentials cannot get the necessary logs. "
                "Please verify that the API settings are correctly configured"
            )
        except requests.exceptions.Timeout as te:
            LOGGER_ERROR.error(
                f"instance={input_name}, "
                f"error_type=Timeout, "
                f"error_code={type(te).__name__}, "
                f"error_detail=Unable to process {input_name}, "
                f"traceback={te}, "
                f"filter_value=sbg_sna_input.py, "
            )
            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "error_type=Timeout, "
                "product=SNA, "
                "filter_value=sbg_sna_input.py, "
                f"error_code={type(te).__name__}, "
                "status=Not Connected, "
            )

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        """The method called to stream events into Splunk.
        It should do all its output through an EventWriter,
        which writes events and error messages from the module input.

        :param inputs: An ``InputDefinition`` object.
        :param event_writer: An object with methods to write events and log messages to
        Splunk.
        """
        exception = error_type = None
        possible_failure_reason = ""
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            try:
                session_key = self._input_definition.metadata["session_key"]
                config = SNAConfig.from_input_item(input_name, input_item, session_key)

                if config.interval is None:
                    LOGGER.error("Missing required arguments, aborting RESTx "
                                 "API process")
                    raise ValueError("The earliest or latest value is missed")

                LOGGER.info(
                    "Configuration processing completed. Setting LOGGER level "
                    f"for {normalized_input_name} to {config.logging_level}"
                )

                status_is_successful = collect_events(
                    config,
                    event_writer,
                    normalized_input_name,
                )

                LOGGER.info(f"Finish SNA input: {normalized_input_name}")
                if status_is_successful:
                    LOGGER_STATUS.info(
                        f"instance={normalized_input_name}, "
                        "product=SNA, "
                        "filter_value=sbg_sna_input.py, "
                        "status=Connected,"
                    )
                else:
                    LOGGER_STATUS.info(
                        f"instance={normalized_input_name}, "
                        "error_type=Configuration, "
                        "product=SNA, "
                        "filter_value=sbg_sna_input.py, "
                        "status=Not Connected, "
                    )
            except AttributeError as ae:
                exception = ae
                error_type = "Configuration"
            except KVStoreTimeoutError as kte:
                exception = kte
                error_type = "KVStoreTimeoutError"
                possible_failure_reason = "KVStore has failed to start"
            except requests.exceptions.Timeout as te:
                exception = te
                error_type = "Timeout"
            except Exception as e:
                exception = e
                error_type = "Uncategorized"
            finally:
                if exception:
                    LOGGER_ERROR.error(
                        f"instance={normalized_input_name}, "
                        f"error_type={error_type}, "
                        f"error_code={type(exception).__name__}, "
                        f"error_detail=Unable to process {input_name}, "
                        f"traceback={exception}, "
                        f"filter_value=sbg_sna_input.py"
                    )
                    LOGGER_STATUS.info(
                        f"instance={normalized_input_name}, "
                        f"error_type={error_type}, "
                        "product=SNA, "
                        "filter_value=sbg_sna_input.py, "
                        f"error_code={type(exception).__name__}, "
                        f"possible_failure_reason={possible_failure_reason}, "
                        "status=Not Connected,"
                    )


if __name__ == "__main__":
    exit_code = SBGSNAInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover
