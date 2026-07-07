import sys  # noqa: I001

import import_declare_test  # noqa
from CiscoSecurityCloud.secret_storage_manager import SecretsStorageManager
from CiscoSecurityCloud.sma.collect_submissions import (
    collect_submissions,
)
from CiscoSecurityCloud.sma.utils import (
    SMAConfig,
    validate_credentials,
)
from CiscoSecurityCloud.utils import create_and_configure_logger
from splunklib import modularinput as smi

LOGGER = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class CiscoSMAInput(smi.Script):
    """A base class that extends :class:`smi.Script`
    for implementing modular input Secure Malware Analytics.

    Methods ``get_scheme``, ``stream_events``,
    and ``validate_input`` for external validation.
    """

    def __init__(self):
        super().__init__()

    def get_scheme(self) -> smi.Scheme:
        """The scheme defines the parameters understood by this modular input.

        :return: ``Scheme`` object representing the parameters for this modular input.
        """
        scheme = smi.Scheme("Cisco SMA Input")
        scheme.description = "Cisco SMA Input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "api_host",
                title="API Host",
                description="Host of the API",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "loglevel",
                title="Log Level",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "after",
                title="After",
                required_on_create=True,
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
        input_name = definition.metadata["name"]
        session_key = definition.metadata["session_key"]
        secret_storage_manager = SecretsStorageManager(session_key=session_key)
        error_data = exception = None

        try:
            validate_credentials(input_values, secret_storage_manager, input_name)
            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "product=Secure Malware Analytics, "
                "filter_value=cisco_sma_input.py, "
                "status=Connected"
            )
        except RuntimeError as re:
            exception = re
            error_data = {
                "error_type": "Throttling",
                "error_detail": "SMA API credentials failed to get token",
                "error_code": "Invalid creds",
                "possible_reason": "Invalid SMA API credentials",
                "possible_resolution": "Update SMA API credentials",
                "value_error": "The provided SMA API credentials cannot provide access"
                " for submissions. Please verify that the SMA API "
                "settings are correctly configured.",
            }
        except Exception as ex:
            exception = ex
            error_data = {
                "error_type": "Uncategorized",
                "error_detail": "Unhandled exception when validating SMA API "
                "credentials",
                "error_code": "Invalid creds",
                "value_error": f"Unhandled exception when validating SMA API "
                f"credentials: {ex}",
            }
        finally:
            if exception:
                LOGGER_ERROR.error(
                    f"instance={input_name}, "
                    f"error_type={error_data.get('error_type')}, "
                    f"error_code={type(exception).__name__}, "
                    f"error_detail={error_data.get('error_detail')}, "
                    f"filter_value=cisco_sma_input.py, "
                    f"possible_reason={error_data.get('possible_reason', '')}, "
                    f"possible_resolution={error_data.get('possible_resolution', '')}, "
                    f"traceback={exception},"
                )
                LOGGER_STATUS.info(
                    f"instance={input_name}, "
                    f"error_type={error_data.get('error_type')}, "
                    "product=Secure Malware Analytics, "
                    "filter_value=cisco_sma_input.py, "
                    f"error_code={error_data.get('error_code')}, "
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
        :param event_writer: An object with methods to write events and log messages to
        Splunk.
        """

        exception = error_type = None
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            try:
                LOGGER.info(f"Start Cisco SMA input: {normalized_input_name}")

                session_key = self._input_definition.metadata["session_key"]
                config = SMAConfig.from_input_item(input_item, input_name, session_key)

                collect_submissions(config, event_writer)

                LOGGER.info(f"End Cisco SMA input: {normalized_input_name}")
                LOGGER_STATUS.info(
                    f"instance={normalized_input_name}, "
                    "product=Secure Malware Analytics, "
                    "filter_value=cisco_sma_input.py, "
                    "status=Connected"
                )
            except AttributeError as ae:
                exception = ae
                error_type = "Configuration"
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
                        f"filter_value=cisco_sma_input.py"
                    )
                    LOGGER_STATUS.info(
                        f"instance={normalized_input_name}, "
                        f"error_type={error_type}, "
                        "product=Secure Malware Analytics, "
                        "filter_value=cisco_sma_input.py, "
                        f"error_code={type(exception).__name__}, "
                        "status=Not Connected,"
                    )


if __name__ == "__main__":
    exit_code = CiscoSMAInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover
