import socket  # noqa: I001
import sys
import struct

import import_declare_test  # noqa: F401

from splunklib import modularinput as smi

from CiscoSecurityCloud.exceptions import KVStoreTimeoutError
from CiscoSecurityCloud.utils import create_and_configure_logger
from CiscoSecurityCloud.fw_estreamer.collect_events import (
    collect_events,
    validate_connection,
)
from CiscoSecurityCloud.fw_estreamer.exceptions import (
    CertificateUnavailableException,
    InvalidCertificateDecodingException,
    CertificateProcessingError,
)
from CiscoSecurityCloud.fw_estreamer.utils import EStreamerConfig, write_bookmark

LOGGER = create_and_configure_logger(__name__)
LOGGER_DATA = create_and_configure_logger(name="data")
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class SBGFWInput(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("SBG Firewall eStreamer Input")
        scheme.description = "Get log data from the Secure Firewall eStreamer."
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "fmc_host",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "fmc_port",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "event_types",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "estreamer_import_time_range",
                title="Import time range",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition):
        exception = None
        error_data = None

        input_name = definition.metadata["name"]
        session_key = definition.metadata["session_key"]
        parameters = definition.parameters
        try:
            host = parameters.get("fmc_host")
            port = parameters.get("fmc_port")
            config_map = EStreamerConfig.prepare_config_map(
                parameters.get("event_types")
            )
            password, certificate = EStreamerConfig.get_password_and_certificate(
                input_name, session_key
            )

            validate_connection(
                input_name, host, port, password, certificate, config_map
            )
        except CertificateUnavailableException as e:
            exception = e
            error_data = {
                "error_type": "CertificateError",
                "error_detail": "Cannot read certificate from storage",
                "value_error": (
                    "Cannot read certificate from storage. "
                    "Please verify that certificate is stored correctly in "
                    "passwords.conf."
                ),
            }
        except InvalidCertificateDecodingException as e:
            exception = e
            error_data = {
                "error_type": "CertificateError",
                "error_detail": "Cannot generate certificate file from base64",
                "value_error": (
                    "Cannot generate certificate file. "
                    "Please verify that certificate is stored correctly in "
                    "passwords.conf."
                ),
            }
        except CertificateProcessingError as ce:
            exception = ce
            error_data = {
                "error_type": "CertificateError",
                "error_detail": "Cannot generate .cert and .key from pkcs12",
                "value_error": (
                    f"The input with provided configuration cannot be processed "
                    f"due to error with generating .cert and .key from pkcs12. "
                    f"{ce}"
                ),
            }
        except socket.gaierror as e:
            exception = e
            error_data = {
                "error_type": "Connection",
                "error_detail": (
                    "Probably host name is invalid or the certificate was issued for "
                    "another host."
                ),
                "value_error": (
                    "The input with provided configuration cannot be processed "
                    "due to invalid host or the certificate was issued for "
                    "another host."
                ),
            }
        except socket.timeout as se:
            exception = se
            error_data = {
                "error_type": "TimeoutError",
                "error_detail": "Socket issue",
                "value_error": "Cannot retrieve data from eStreamer due to Timeout "
                "error.",
            }
        except struct.error as se:
            exception = se
            error_data = {
                "error_type": "Connection",
                "error_detail": "Struct error occurred, probably invalid format of "
                "data",
                "value_error": (
                    "Cannot retrieve data from eStreamer. "
                    "Please verify that the certificate and password are valid "
                    "and the certificate was issued for valid host. "
                    "Please keep in mind, that the certificate should be "
                    "generated with your Splunk host as name."
                ),
            }
        except PermissionError as e:
            exception = e
            error_data = {
                "error_type": "PermissionError",
                "error_detail": "Permissions error during input configuration",
                "value_error": (
                    f"The input with provided configuration cannot be processed "
                    f"due to PermissionError. It is possible that you do not have "
                    f"sufficient permissions to manage the file system, particularly "
                    f"permissions to write files into the HOME directory. "
                    f"Error Details: {e}"
                ),
            }
        except Exception as e:
            exception = e
            error_data = {
                "error_type": "Uncategorized",
                "error_detail": "Uncategorized",
                "value_error": (
                    f"The input with provided configuration cannot be processed "
                    f"due to {type(e).__name__}: {e}"
                ),
            }
        finally:
            if exception:
                LOGGER_ERROR.error(
                    f"instance={input_name}, "
                    f"error_type={error_data.get('error_type')}, "
                    f"error_code={type(exception).__name__}, "
                    f"error_detail={error_data.get('error_detail')}, "
                    f"traceback={exception}, "
                    f"filter_value=sbg_fw_estreamer_input.py, "
                )
                raise ValueError(error_data.get("value_error"))

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        exception = error_data = None

        for input_name, input_item in inputs.inputs.items():
            LOGGER.info("Getting input configuration for eStreamer.")
            normalized_input_name = input_name.split("/")[-1]
            try:
                LOGGER.info(f"Start eStreamer input: {normalized_input_name}")
                session_key = self._input_definition.metadata["session_key"]

                config = EStreamerConfig.from_input_item(
                    input_item, input_name, session_key
                )

                collect_events(config, event_writer)

                LOGGER.info(f"Finish eStreamer input: {normalized_input_name}")
                LOGGER_DATA.info(
                    f"instance={normalized_input_name}, "
                    "name=sfw, "
                    "filter_value=sbg_fw_estreamer_input.py"
                )

                LOGGER_STATUS.info(
                    f"instance={normalized_input_name}, "
                    "product=Firewall eStreamer, "
                    "filter_value=sbg_fw_estreamer_input.py, "
                    "status=Connected"
                )
            except KVStoreTimeoutError as kte:
                exception = kte
                error_data = {
                    "error_type": "KVStoreTimeoutError",
                    "possible_failure_reason": "KVStore has failed to start",
                }
            except PermissionError as e:
                exception = e
                error_data = {
                    "error_type": "PermissionError",
                    "possible_failure_reason": (
                        "Not enough permissions to manage file system, especially "
                        "permissions to write files into HOME directory. More context"
                    ),
                }
            except socket.gaierror as e:
                exception = e
                error_data = {
                    "error_type": "Connection",
                    "possible_failure_reason": "Invalid host",
                }
            except socket.timeout as se:
                exception = se
                error_data = {
                    "error_type": "TimeoutError",
                    "possible_failure_reason": (
                        "Cannot retrieve data from eStreamer due to Timeout error"
                    ),
                }
            except socket.error as se:
                exception = se
                error_data = {
                    "error_type": "Connection",
                    "possible_failure_reason": "Connection issue",
                }
            except struct.error as se:
                exception = se
                error_data = {
                    "error_type": "Connection",
                    "possible_failure_reason": "Invalid format of data",
                }
            except (
                CertificateUnavailableException,
                InvalidCertificateDecodingException,
            ) as ce:
                exception = ce
                error_data = {
                    "error_type": "CertificateError",
                    "possible_failure_reason": "Wrong certificate",
                }
            except CertificateProcessingError as ce:
                exception = ce
                error_data = {
                    "error_type": "CertificateError",
                    "possible_failure_reason": (
                        "Error with generating .cert and .key from pkcs12."
                    ),
                }
            except (AttributeError, TypeError) as ae:
                exception = ae
                error_data = {
                    "error_type": "Configuration",
                    "possible_failure_reason": (
                        "The input could have invalid setup. Edit input configuration "
                        "or re-create input if it does not help"
                    ),
                }
            except Exception as e:
                exception = e
                error_data = {
                    "error_type": "Uncategorized",
                    "possible_failure_reason": "Uncategorized",
                }
            finally:
                if exception:
                    write_bookmark(
                        f"error_type={error_data.get('error_type')}, "
                        f"error_detail=Unable to process {input_name}, "
                        f"error_code={type(exception).__name__}, "
                        f"traceback={exception},"
                    )
                    LOGGER_ERROR.error(
                        f"instance={normalized_input_name}, "
                        f"error_type={error_data.get('error_type')}, "
                        f"error_code={type(exception).__name__}, "
                        f"error_detail=Unable to process {input_name}, "
                        f"traceback={exception}, "
                        f"filter_value=sbg_fw_estreamer_input.py"
                    )
                    LOGGER_STATUS.info(
                        f"instance={normalized_input_name}, "
                        f"error_type={error_data.get('error_type')}, "
                        "product=Firewall eStreamer, "
                        "filter_value=sbg_fw_estreamer_input.py, "
                        f"error_code={type(exception).__name__}, "
                        f"possible_failure_reason="
                        f"{error_data.get('possible_failure_reason')}, "
                        "status=Not Connected,"
                        f"traceback={exception}"
                    )


if __name__ == "__main__":
    exit_code = SBGFWInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover
