import sys  # noqa: I001

import import_declare_test  # noqa

from splunklib import modularinput as smi

from CiscoSecurityCloud.config import SE_INPUT_KEY
from CiscoSecurityCloud.exceptions import KVStoreTimeoutError
from CiscoSecurityCloud.secret_storage_manager import SecretsStorageManager
from CiscoSecurityCloud.utils import create_and_configure_logger
from CiscoSecurityCloud.secure_endpoint.collect_events import collect_events

from CiscoSecurityCloud.secure_endpoint.utils import (
    SEConfig,
    ping_api
)

LOGGER = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class SecureEndpointInput(smi.Script):
    """A base class that extends :class:`smi.Script`
    for implementing modular input Secure Endpoint.

    Methods ``get_scheme``, ``stream_events``,
    and ``validate_input`` for external validation.
    """
    def __init__(self):
        super().__init__()

    def get_scheme(self) -> smi.Scheme:
        """The scheme defines the parameters understood by this modular input.

        :return: ``Scheme`` object representing the parameters for this modular input.
        """
        scheme = smi.Scheme("sbg_se_input")
        scheme.description = "Cisco Secure Endpoint"
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
        scheme.add_argument(
            smi.Argument(
                "client_id",
                required_on_create=True,
            )
        ),
        scheme.add_argument(
            smi.Argument(
                "event_types",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "groups",
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
        client_id = input_values.get("client_id")
        api_host = input_values.get("api_host")
        api_key = SecretsStorageManager(
            session_key=definition.metadata["session_key"]
        ).get_secret(
            username=f"{input_name}_api_key",
            realm=SE_INPUT_KEY
        )

        try:
            ping_api(input_name, api_host, client_id, api_key)

            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "product=Secure Endpoint, "
                "filter_value=sbg_se_input.py, "
                "status=Connected"
            )
        except Exception as ex:
            LOGGER_ERROR.error(
                f"instance={input_name}, "
                f"error_type=Uncategorized, "
                f"error_code={type(ex).__name__}, "
                f"error_detail=Unhandled exception when validating "
                f"Secure Endpoint API credentials, "
                f"filter_value=sbg_se_input.py, "
                f"traceback={ex},"
            )
            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "error_type=Uncategorized, "
                "product=Secure Endpoint, "
                "filter_value=sbg_se_input.py, "
                "error_code=Invalid creds, "
                "status=Not Connected,"
            )
            raise ValueError(
                f"Unhandled exception when validating "
                f"Secure Endpoint API credentials: {ex}"
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
                LOGGER.info(f"Start Cisco SE input:{normalized_input_name}")
                session_key = self._input_definition.metadata["session_key"]

                config = SEConfig.from_input_item(input_item, input_name, session_key)

                LOGGER.info(
                    "Configuration processing completed. "
                    "Setting LOGGER level "
                    "for %s to %s",
                    normalized_input_name,
                    config.logging_level,
                )

                collect_events(config, event_writer, normalized_input_name, session_key)

                LOGGER.info(f"End Cisco Secure Endpoint input: {normalized_input_name}")
                LOGGER_STATUS.info(
                    f"instance={normalized_input_name}, "
                    "product=Secure Endpoint, "
                    "filter_value=sbg_se_input.py, "
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
                        f"filter_value=sbg_se_input.py"
                    )
                    LOGGER_STATUS.info(
                        f"instance={normalized_input_name}, "
                        f"error_type={error_type}, "
                        "product=Secure Endpoint, "
                        "filter_value=sbg_se_input.py, "
                        f"error_code={type(exception).__name__}, "
                        f"possible_failure_reason={possible_failure_reason}, "
                        "status=Not Connected,"
                    )


if __name__ == "__main__":
    exit_code = SecureEndpointInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover
