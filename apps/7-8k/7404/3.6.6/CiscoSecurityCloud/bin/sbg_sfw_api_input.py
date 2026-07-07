import sys  # noqa: I001
import requests

import import_declare_test  # noqa

from splunklib import modularinput as smi

from CiscoSecurityCloud.utils import create_and_configure_logger
from CiscoSecurityCloud.fmc_api.collect_events import collect_events
from CiscoSecurityCloud.fmc_api.exceptions import (
    PolicyRetrieveException,
    CredentialsError,
)
from CiscoSecurityCloud.fmc_api.utils import FMCAPIConfig
from CiscoSecurityCloud.fmc_api.fmc_api_client import FMCApiClient


LOGGER = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class SBGSFWAPIInput(smi.Script):
    def __init__(self):
        super(SBGSFWAPIInput, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("sbg_sfw_api_input")
        scheme.description = "Secure Firewall API"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "fmc_host",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        input_name = definition.metadata["name"]
        session_key = definition.metadata["session_key"]
        input_item = definition.parameters
        error_data = exception = None
        try:
            config = FMCAPIConfig.from_input_item(input_name, input_item, session_key)
            fmc_api_client = FMCApiClient(config, input_name)

            fmc_api_client.login()
            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "product=Secure Firewall API, "
                "filter_value=sbg_sfw_api_input.py, "
                "status=Connected,"
            )
        except requests.exceptions.ConnectionError as ce:
            exception = ce
            error_data = {
                "error_type": "Configuration",
                "value_error": "The provided API credentials cannot get the necessary "
                "data. Please verify that the FMC host is valid.",
            }
        except requests.exceptions.Timeout as te:
            exception = te
            error_data = {
                "error_type": "Timeout",
                "value_error": "Cannot retrieve data from FMC API due to Timeout "
                "error.",
            }
        except CredentialsError as ce:
            exception = ce
            error_data = {
                "error_type": "Authentication",
                "value_error": "Cannot retrieve data from FMC API due to login error. "
                "Please verify your API credentials.",
            }
        except PolicyRetrieveException as e:
            exception = e
            error_data = {
                "error_type": "APIError",
                "value_error": f"Cannot retrieve data from FMC API due to unexpected "
                f"API response. {e}",
            }
        except Exception as e:
            exception = e
            error_data = {
                "error_type": "Uncategorized",
                "value_error": "The input with provided configuration cannot be "
                f"processed duo to unexpected error: {e}",
            }
        finally:
            if exception:
                LOGGER_ERROR.error(
                    f"instance={input_name}, "
                    f"error_type={error_data.get('error_type')}, "
                    f"error_code={type(exception).__name__}, "
                    f"error_detail=Unable to process {input_name}, "
                    f"traceback={exception}, "
                    f"filter_value=sbg_sfw_api_input.py, "
                )
                LOGGER_STATUS.info(
                    f"instance={input_name}, "
                    f"error_type={error_data.get('error_type')}, "
                    "product=Secure Firewall API, "
                    "filter_value=sbg_sfw_api_input.py, "
                    f"error_code={error_data.get('error_code')}, "
                    "status=Not Connected,"
                )
                raise ValueError(error_data.get("value_error"))

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            error_data = exception = None
            try:
                LOGGER.info(f"Start Secure Firewall API input:{normalized_input_name}")
                session_key = self._input_definition.metadata["session_key"]

                config = FMCAPIConfig.from_input_item(
                    input_name, input_item, session_key
                )
                LOGGER.info("Collect events Secure Firewall APIstarted")
                collect_events(config, ew, normalized_input_name)

                LOGGER.info(f"End Secure Firewall API input: {normalized_input_name}")

                LOGGER_STATUS.info(
                    f"instance={normalized_input_name}, "
                    "product=Secure Firewall API, "
                    "filter_value=sbg_sfw_api_input.py, "
                    "status=Connected, "
                )
            except requests.exceptions.ConnectionError as ce:
                exception = ce
                error_data = {
                    "error_type": "Configuration",
                    "possible_failure_reason": "The provided API credentials cannot "
                    "get the necessary data. Verify that the"
                    " FMC host is valid",
                }
            except requests.exceptions.Timeout as te:
                exception = te
                error_data = {
                    "error_type": "Timeout",
                    "possible_failure_reason": "Cannot retrieve data from API due to "
                    "Timeout error",
                }
            except CredentialsError as ce:
                exception = ce
                error_data = {
                    "error_type": "Authentication",
                    "possible_failure_reason": "Cannot retrieve data from FMC API due "
                    "to login error. Please verify your API "
                    "credentials.",
                }
            except PolicyRetrieveException as e:
                exception = e
                error_data = {"error_type": "APIError"}
            except Exception as e:
                exception = e
                error_data = {"error_type": "Uncategorized"}
            finally:
                if exception:
                    LOGGER_ERROR.error(
                        f"instance={input_name}, "
                        f"error_type={error_data.get('error_type')}, "
                        f"error_code={type(exception).__name__}, "
                        f"error_detail=Unable to process {input_name}, "
                        f"traceback={exception}, "
                        f"filter_value=sbg_sfw_api_input.py"
                    )
                    LOGGER_STATUS.info(
                        f"instance={input_name}, "
                        f"error_type={error_data.get('error_type')}, "
                        "product=Secure Firewall API, "
                        "filter_value=sbg_sfw_api_input.py, "
                        f"error_code={type(exception).__name__}, "
                        f"possible_failure_reason="
                        f"{error_data.get('possible_failure_reason', '')}, "
                        "status=Not Connected,"
                    )
                    raise ValueError(exception)


if __name__ == "__main__":
    exit_code = SBGSFWAPIInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover
