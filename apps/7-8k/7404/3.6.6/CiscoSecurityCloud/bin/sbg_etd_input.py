import sys  # noqa: I001

import requests

import import_declare_test  # noqa

from splunklib import modularinput as smi

from CiscoSecurityCloud.etd.collect_messages import collect_messages
from CiscoSecurityCloud.etd.etd_client import ETDApiClient
from CiscoSecurityCloud.etd.utils import (
    REGIONS,
    ETDConfig,
)
from CiscoSecurityCloud.exceptions import KVStoreTimeoutError
from CiscoSecurityCloud.secret_storage_manager import SecretsStorageManager
from CiscoSecurityCloud.utils import create_and_configure_logger

LOGGER = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class CiscoETDInput(smi.Script):
    """A base class that extends :class:`smi.Script`
    for implementing modular input Cisco Secure Email Threat Defense.

    Methods ``get_scheme``, ``stream_events``,
    and ``validate_input`` for external validation.
    """
    def __init__(self):
        super().__init__()

    def get_scheme(self) -> smi.Scheme:
        """The scheme defines the parameters understood by this modular input.

        :return: ``Scheme`` object representing the parameters for this modular input.
        """
        scheme = smi.Scheme("SBG Email Threat Defense Input")
        scheme.description = "SBG Email Threat Defense Input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "client_id",
                title="Client ID",
                description="Product Client ID",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "etd_region",
                title="ETD Region",
                description="Product Client Region",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "etd_import_time_range",
                title="Import time range",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "etd_log_types",
                title="Log types",
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition) -> None:
        """Handles external validation for modular input.

        If this function does not throw an exception, the validation is assumed
        to succeed. Otherwise, any errors thrown will be turned into a string and
        logged back to Splunk.

        :param definition: The parameters for the proposed input passed by splunk.
        """
        input_values = definition.parameters
        input_values["etd_region"] = (
            input_values["etd_region"]
            if input_values["etd_region"] in REGIONS
            else REGIONS[0]
        )

        input_name = definition.metadata["name"]
        session_key = definition.metadata["session_key"]
        error_data = exception = None

        try:
            secret_storage_manager = SecretsStorageManager(session_key=session_key)

            ETDApiClient.get_token_on_validation(
                input_values=input_values,
                input_name=input_name,
                secret_storage_manager=secret_storage_manager
            )

            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "product=Email Threat Defense, "
                "filter_value=sbg_etd_input.py, "
                "status=Connected"
            )
        except RuntimeError as re:
            exception = re
            error_data = {
                "error_type": "Throttling",
                "error_detail": "ETD API credentials failed to get token",
                "value_error": "The provided ETD API credentials cannot get the "
                               "auth token. Please verify that the ETD API settings are"
                               " correctly configured.",
                "possible_reason": "Invalid ETD API credentials",
                "possible_resolution": "Update ETD API credentials",
            }
        except requests.exceptions.Timeout as te:
            exception = te
            error_data = {
                "error_type": "Timeout",
                "error_detail": f"Unable to process {input_name}",
                "value_error": f"Timeout exception when validating ETD API credentials:"
                               f" {te}",
            }
        except Exception as ex:
            exception = ex
            error_data = {
                "error_type": "Uncategorized",
                "error_detail": "Unhandled exception when validating ETD API "
                                "credentials",
                "value_error": f"Unhandled exception when validating ETD API "
                               f"credentials: {ex}",
            }
        finally:
            if exception:
                LOGGER_ERROR.error(
                    f"instance={input_name}, "
                    f"error_type={error_data.get('error_type')}, "
                    f"error_code={type(exception).__name__}, "
                    f"error_detail={error_data.get('error_detail')}, "
                    f"filter_value=sbg_etd_input.py, "
                    f"possible_reason={error_data.get('possible_reason', '')}, "
                    f"possible_resolution={error_data.get('possible_resolution', '')}, "
                    f"traceback={exception},"
                )
                LOGGER_STATUS.info(
                    f"instance={input_name}, "
                    f"error_type={error_data.get('error_type')}, "
                    "product=Email Threat Defense, "
                    "filter_value=sbg_etd_input.py, "
                    "error_code=Invalid creds, "
                    "status=Not Connected,"
                )
                raise ValueError(error_data.get("value_error"))

    def stream_events(
        self, inputs: smi.InputDefinition, event_writer: smi.EventWriter
    ) -> None:
        """The method called to stream events into Splunk.
        It should do all its output through an EventWriter,
        which writes events and error messages from the module input.

        :param inputs: An ``InputDefinition`` object.
        :param event_writer: An object with methods to write events and log messages
        to Splunk.
        """
        exception = error_type = None
        possible_failure_reason = ""
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            try:
                LOGGER.info(f"Start Cisco ETD input: {normalized_input_name}")

                session_key = self._input_definition.metadata["session_key"]
                config = ETDConfig.from_input_item(input_name, input_item, session_key)

                LOGGER.info(
                    "Configuration processing completed. Setting LOGGER level "
                    "for %s to %s",
                    normalized_input_name,
                    config.logging_level,
                )

                collect_messages(
                    config,
                    event_writer,
                    session_key,
                    normalized_input_name,
                )

                LOGGER.info(f"Finish ETD input: {normalized_input_name}")
                LOGGER_STATUS.info(
                    f"instance={normalized_input_name}, "
                    "product=Email Threat Defense, "
                    "filter_value=sbg_etd_input.py, "
                    "status=Connected"
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
                        f"filter_value=sbg_etd_input.py"
                    )
                    LOGGER_STATUS.info(
                        f"instance={normalized_input_name}, "
                        f"error_type={error_type}, "
                        "product=Email Threat Defense, "
                        "filter_value=sbg_etd_input.py, "
                        f"error_code={type(exception).__name__}, "
                        f"possible_failure_reason={possible_failure_reason}, "
                        "status=Not Connected,"
                    )


if __name__ == "__main__":
    exit_code = CiscoETDInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover
