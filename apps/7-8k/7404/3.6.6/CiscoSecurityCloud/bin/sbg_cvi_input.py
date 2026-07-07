import import_declare_test  # noqa

import sys  # noqa: I001

from splunklib import modularinput as smi

from CiscoSecurityCloud.config import CVI_INPUT_KEY
from CiscoSecurityCloud.cvi.collect_events import collect_events
from CiscoSecurityCloud.secret_storage_manager import SecretsStorageManager
from CiscoSecurityCloud.cvi.utils import (
    CVIConfig,
    make_test_request
)
from CiscoSecurityCloud.exceptions import KVStoreTimeoutError
from CiscoSecurityCloud.utils import create_and_configure_logger

LOGGER = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class SBGCVIInput(smi.Script):
    """A base class that extends :class:`smi.Script`
    for implementing modular input Cisco Vulnerability Intelligence.

    Methods ``get_scheme``, ``stream_events``,
    and ``validate_input`` for external validation.
    """
    def __init__(self):
        super(SBGCVIInput, self).__init__()

    def get_scheme(self) -> smi.Scheme:
        """The scheme defines the parameters understood by this modular input.

        :return: ``Scheme`` object representing the parameters for this modular input.
        """
        scheme = smi.Scheme("SBG Cisco Vulnerability Intelligence Input")
        scheme.description = "SBG Cisco Vulnerability Intelligence Input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name",
                title="Name",
                description="Name",
                required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "api_host",
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
        cvi_api_host = input_values.get("api_host")
        cvi_api_key = SecretsStorageManager(
            session_key=definition.metadata["session_key"]
        ).get_secret(
            username=f"{input_name}_api_key",
            realm=CVI_INPUT_KEY
        )

        try:
            make_test_request(input_name, cvi_api_host, cvi_api_key)

            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "product=Cisco Vulnerability Intelligence, "
                "filter_value=sbg_cvi_input.py, "
                "status=Connected"
            )
        except Exception as ex:
            LOGGER_ERROR.error(
                f"instance={input_name}, "
                f"error_type=Uncategorized, "
                f"error_code={type(ex).__name__}, "
                f"error_detail=Unhandled exception when validating "
                f"Cisco Vulnerability Intelligence API credentials, "
                f"filter_value=sbg_cvi_input.py, "
                f"traceback={ex},"
            )
            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "error_type=Uncategorized, "
                "product=Cisco Vulnerability Intelligence, "
                "filter_value=sbg_cvi_input.py, "
                "error_code=Invalid creds, "
                "status=Not Connected,"
            )
            raise ValueError(
                f"Unhandled exception when validating "
                f"Cisco Vulnerability Intelligence API credentials: {ex}"
            )

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
        possible_failure_reason = ""
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            try:
                LOGGER.info(f"Start Cisco CVI input: {normalized_input_name}")

                session_key = self._input_definition.metadata["session_key"]
                config = CVIConfig.from_input_item(input_name, input_item, session_key)

                LOGGER.info(
                    "Configuration processing completed. Setting LOGGER level "
                    "for %s to %s",
                    normalized_input_name,
                    config.logging_level,
                )

                collect_events(
                    config,
                    event_writer,
                    session_key,
                    normalized_input_name,
                )

                LOGGER.info(f"Finish CVI input: {normalized_input_name}")
                LOGGER_STATUS.info(
                    f"instance={normalized_input_name}, "
                    "product=Cisco Vulnerability Intelligence, "
                    "filter_value=sbg_cvi_input.py, "
                    "status=Connected"
                )
            except AttributeError as ae:
                exception = ae
                error_type = "Configuration"
            except KVStoreTimeoutError as kte:
                exception = kte
                error_type = "KVStoreTimeoutError"
                possible_failure_reason = "KVStore has failed to start"
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
                        f"filter_value=sbg_cvi_input.py"
                    )
                    LOGGER_STATUS.info(
                        f"instance={normalized_input_name}, "
                        f"error_type={error_type}, "
                        "product=Cisco Vulnerability Intelligence, "
                        "filter_value=sbg_cvi_input.py, "
                        f"error_code={type(exception).__name__}, "
                        f"possible_failure_reason={possible_failure_reason}, "
                        "status=Not Connected,"
                    )


if __name__ == "__main__":
    exit_code = SBGCVIInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover
