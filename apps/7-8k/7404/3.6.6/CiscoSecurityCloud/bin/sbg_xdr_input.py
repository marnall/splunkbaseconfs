import sys  # noqa: I001

import requests
import import_declare_test  # noqa

from splunklib import modularinput as smi

from CiscoSecurityCloud.exceptions import KVStoreTimeoutError
from CiscoSecurityCloud.secret_storage_manager import SecretsStorageManager
from CiscoSecurityCloud.utils import create_and_configure_logger
from CiscoSecurityCloud.xdr.collect_incidents import collect_incidents
from CiscoSecurityCloud.xdr.credentials_manager import CredentialsManager
from CiscoSecurityCloud.xdr.utils import XDRConfig, REGIONS


LOGGER = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class CiscoXDRInput(smi.Script):
    """A base class that extends :class:`smi.Script`
    for implementing modular input XDR.

    Methods ``get_scheme``, ``stream_events``,
    and ``validate_input`` for external validation.
    """
    def __init__(self):
        super().__init__()

    def get_scheme(self) -> smi.Scheme:
        """The scheme defines the parameters understood by this modular input.

        :return: ``Scheme`` object representing the parameters for this modular input.
        """
        scheme = smi.Scheme("Cisco XDR Input")
        scheme.description = "Cisco XDR Input"
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
                "region",
                title="Region",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "auth_method",
                title="Authentication Method",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "xdr_import_time_range",
                title="Import time range",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "incidents",
                title="Incidents",
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
        region = (
            input_values["region"]
            if input_values["region"] in REGIONS
            else REGIONS[0]
        )
        input_name = definition.metadata["name"]
        try:
            CredentialsManager(
                client_id=input_values.get("client_id"),
                region=region,
                input_name=input_name,
                secrets_storage_manager=SecretsStorageManager(
                    session_key=definition.metadata["session_key"]
                )
            ).validate_credentials(input_values.get("auth_method"))
            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "product=Xdr, "
                "filter_value=sbg_xdr_input.py, "
                "status=Connected"
            )
        except requests.exceptions.Timeout as te:
            LOGGER_ERROR.error(
                f"instance={input_name}, "
                f"error_type=Timeout, "
                f"error_code={type(te).__name__}, "
                f"error_detail=Unable to process {input_name}, "
                f"traceback={te}, "
                f"filter_value=sbg_xdr_input.py"
            )
            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "error_type=Timeout, "
                "product=XDR, "
                "filter_value=sbg_xdr_input.py, "
                f"error_code={type(te).__name__}, "
                "status=Not Connected,"
            )
            raise ValueError(
                f"Timeout exception when validating XDR API credentials: {te}"
            )
        except Exception as ex:
            LOGGER_ERROR.error(
                f"instance={input_name}, "
                f"error_type=Uncategorized, "
                f"error_code={type(ex).__name__}, "
                f"error_detail=Unhandled exception when validating "
                f"XDR API credentials, "
                f"filter_value=sbg_xdr_input.py, "
                f"traceback={ex},"
            )
            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "error_type=Uncategorized, "
                "product=Xdr, "
                "filter_value=sbg_xdr_input.py, "
                "error_code=Invalid creds, "
                "status=Not Connected,"
            )
            raise ValueError(
                f"Unhandled exception when validating XDR API credentials: {ex}"
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
                LOGGER.info(f"Start Cisco XDR input: {normalized_input_name}")

                session_key = self._input_definition.metadata["session_key"]
                config = XDRConfig.from_input_item(input_name, input_item, session_key)

                LOGGER.info(
                    "Configuration processing completed. Setting LOGGER level for "
                    f"{normalized_input_name} to {config.logging_level}"
                )

                collect_incidents(
                    config,
                    event_writer,
                    session_key,
                    normalized_input_name,
                    input_item.get("client_id")
                )

                LOGGER_STATUS.info(
                    f"instance={normalized_input_name}, "
                    "product=XDR, "
                    "filter_value=sbg_xdr_input.py, "
                    "status=Connected"
                )
            except requests.exceptions.Timeout as te:
                exception = te
                error_type = "Timeout"
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
                        f"filter_value=sbg_xdr_input.py"
                    )
                    LOGGER_STATUS.info(
                        f"instance={normalized_input_name}, "
                        f"error_type={error_type}, "
                        "product=XDR, "
                        "filter_value=sbg_xdr_input.py, "
                        f"error_code={type(exception).__name__}, "
                        f"possible_failure_reason={possible_failure_reason}, "
                        "status=Not Connected,"
                    )


if __name__ == "__main__":
    exit_code = CiscoXDRInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover
