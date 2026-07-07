import base64  # noqa: I001
import hashlib
import logging
import os
import socket
import string
import sys

import import_declare_test  # noqa: F401

import duo_client
from solnlib import utils as solnlib_utils
from splunklib import modularinput as smi

from CiscoSecurityCloud.exceptions import KVStoreTimeoutError
from CiscoSecurityCloud.secret_storage_manager import SecretsStorageManager
from CiscoSecurityCloud.utils import create_and_configure_logger
from CiscoSecurityCloud.config import APP_NAME, DUO_INPUT_KEY
from CiscoSecurityCloud.duo.config import (
    LOCAL_API_HOST,
    LOG_CLASSES,
)
from duo.logclasses.exceptions import MaxRequestAttemptsReached

LOGGER: logging.Logger = create_and_configure_logger(__name__)
LOGGER_ERROR = create_and_configure_logger(name="error")
LOGGER_STATUS = create_and_configure_logger(name="status")


class SBGDuoInput(smi.Script):
    """A base class that extends :class:`smi.Script`
    for implementing modular input DUO.

    Methods ``get_scheme``, ``stream_events``,
    `validate_arguments``, ``prepare_config``, ``get_proxies``, ``_log_attribute_name``
    and ``validate_input`` for external validation.
    """
    def __init__(self):
        super(SBGDuoInput, self).__init__()
        self.encrypted_fields = ["ikey", "skey", "proxy_password"]

    def get_scheme(self) -> smi.Scheme:
        """The scheme defines the parameters understood by this modular input.

        :return: ``Scheme`` object representing the parameters for this modular input.
        """
        scheme = smi.Scheme("Duo Security Log Input")
        scheme.description = "Get log data from the Duo Security Admin API."
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
                "api_host",
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "duo_security_logs",
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "logging_level",
                required_on_create=False,
            )
        )

        return scheme

    def verify_integration_config(self, duo_admin: duo_client.Admin) -> None:
        """Verify the ikey, skey, proxy and api-host by making two different adminapi
        calls. This method supports a min time offset which is used to minify the
        amount of data queried. This method test the account summary and the
        administrator logs admin api endpoint. These two are the minimum number of
        api endpoints that we need to call to verify that the admin has set "Grant
        read information" and "Grant read log" in the integration configuration.

        :param duo_admin: Instance of a duo_client object that can
            communicate with the adminapi. This can raise exceptions when attempting
            to pull logs.

        :return: None: This method simply runs instance methods on the duo_admin param,
            and bubbles up exceptions to the caller if the API call can't be made.
        """
        LOGGER.info(
            "Verifying ikey, skey, proxy and api-host "
            "with sample api calls."
        )

        LOGGER.info("Start testing api call get_info_summary")
        duo_admin.get_info_summary()
        LOGGER.info("Finished testing api call get_info_summary")

    def validate_arguments(
        self, input_values: dict, input_name: str, interval: int, session_key: str
    ) -> None:
        """
        Ensures that the provided credentials have access to different log types
        Also check that the interval is >= 120 seconds to avoid rate limiting.

        :param input_values: Input values from user.
        :param input_name: Name of Input
        :param interval: How often Splunk runs this input script, in seconds.
        :param session_key: Session key of input definition
        """
        if interval < 120:
            LOGGER_ERROR.error(
                f"instance={input_name}, "
                "error_type=Configuration, "
                "error_code=Condition, "
                "error_detail=The interval must be greater than "
                "or equal to 120 seconds, "
                "filter_value=sbg_duo_input.py, "
                "possible_reason=The interval is less than 120 seconds, "
                "possible_resolution=Increase interval runs this input script,"
            )
            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "error_type=Configuration, "
                "product=Duo, "
                "filter_value=sbg_duo_input.py, "
                "error_code=Invalid config, "
                "status=Not Connected,"
            )
            raise ValueError(
                "The interval must be greater than or equal to 120 seconds"
            )
        secret_storage_manager = SecretsStorageManager(session_key=session_key)
        #  grab encrypted data from passwords storage
        #  in order to validate API credentials
        secrets = secret_storage_manager.get_secrets(
            input_name=input_name,
            realm=DUO_INPUT_KEY,
            secrets_keys=self.encrypted_fields
        )
        host = input_values["api_host"]
        admin = duo_client.admin.Admin(
            ikey=secrets["ikey"], skey=secrets["skey"], host=host, timeout=4
        )
        if host == LOCAL_API_HOST:
            admin.ca_certs = "DISABLE"

        proxies = self.get_proxies(input_values, secrets.get("proxy_password"))
        if proxies:
            admin.set_proxy(
                host=proxies["proxy_host"],
                port=proxies["proxy_port"],
                headers=proxies.get("proxy_headers"),
                proxy_type=proxies["proxy_type"]
            )

        error_data = exception = None
        try:
            self.verify_integration_config(admin)

            LOGGER_STATUS.info(
                f"instance={input_name}, "
                "product=Duo, "
                "filter_value=sbg_duo_input.py, "
                "status=Connected"
            )
        # RuntimeError raised from duo_client.Admin calls that result in non-200
        # HTTP response statues. Using utils.log_exception to cram the traceback
        # into a single line because the traceback information doesn't appear in
        # the ModularInput log if it spans more than one line. Re-raising the
        # original exception to bubble that to the top.
        except RuntimeError as re:
            exception = re
            error_data = {
                "error_type": "Throttling",
                "error_code": "Invalid creds",
                "error_detail": "Admin API credentials failed to get logs",
                "value_error": "The provided admin API credentials cannot get the "
                               "necessary logs. Please verify that the Admin API "
                               "settings are correctly configured.",
            }
        except socket.timeout as st:
            exception = st
            error_data = {
                "error_type": "Connection",
                "error_code": "Invalid config",
                "error_detail": f"Unable to connect to Duo Admin API host={host} for "
                                "validation",
                "value_error": "Cannot retrieve data from Duo Admin API due to Timeout "
                               "error.",
            }
        except socket.gaierror as se:
            exception = se
            error_data = {
                "error_type": "Configuration",
                "error_code": "Invalid config",
                "error_detail": f"Unable to connect to API host={host} for validation",
                "value_error": f"Unable to connect to API host={host}. Check that your "
                               "host is configured correctly.",
            }
        except Exception as ex:
            exception = ex
            error_data = {
                "error_type": "Uncategorized",
                "error_code": "Invalid creds",
                "error_detail": "Unhandled exception when validating admin API "
                                "credentials",
                "value_error": "Unhandled exception when validating admin API "
                               f"credentials: {ex}"
            }
        finally:
            if exception:
                LOGGER_ERROR.error(
                    f"instance={input_name}, "
                    f"error_type={error_data.get('error_type')}, "
                    f"error_code={type(exception).__name__}, "
                    f"error_detail={error_data.get('error_detail')}, "
                    f"filter_value=sbg_duo_input.py, "
                    f"traceback={exception},"
                )
                LOGGER_STATUS.info(
                    f"instance={input_name}, "
                    f"error_type={error_data.get('error_type')}, "
                    "product=Duo, "
                    "filter_value=sbg_duo_input.py, "
                    f"error_code={error_data.get('error_code')}, "
                    "status=Not Connected,"
                )
                raise ValueError(error_data.get("value_error"))

    def validate_input(self, definition: smi.ValidationDefinition) -> None:
        """Handles external validation for modular input.

        If this function does not throw an exception, the validation is assumed
        to succeed. Otherwise, any errors thrown will be turned into a string and
        logged back to Splunk.

        :param definition: The parameters for the proposed input passed by splunk.
        """
        def transform_interval(raw_interval: str) -> int:
            """
            If the interval field is not a number, it's either a cron
            schedule, which we won't check, or an invalid interval
            which Splunk will catch. Set this to 120 so it passes validation
            """
            try:
                interval_value = int(raw_interval)
            except (ValueError, KeyError):
                #  XXX We will eventually need to make this work better with cron
                interval_value = 120

            return interval_value

        input_values = definition.parameters
        interval = transform_interval(input_values["interval"])

        self.validate_arguments(
            input_values,
            definition.metadata["name"],
            interval,
            definition.metadata.get("session_key"),
        )

    def prepare_config(
        self, input_name: str, input_item: dict, session_key: str
    ) -> dict:
        """
        Prepares and returns a configuration dictionary.

        :param input_name: The name of the input to be configured.
        :param input_item: A dictionary containing the input items.
        :param session_key: The session key for the configuration.

        :return: dict: A dictionary containing the prepared configuration.
        """
        normalized_input_name = input_name.split("/")[-1]
        secrets = SecretsStorageManager(session_key=session_key).get_secrets(
            input_name=normalized_input_name,
            realm=DUO_INPUT_KEY,
            secrets_keys=self.encrypted_fields
        )

        config = {
            "name": normalized_input_name,
            "api_host": input_item.get("api_host"),
            "index": input_item.get("index"),
            "interval": int(input_item.get("interval")),
            "logging_level": input_item.get("logging_level"),
            "python.version": input_item.get("python.version"),
            "ikey": secrets.get("ikey"),
            "source": input_name,
            "sourcetype": input_item.get("sourcetype"),
            "proxies": self.get_proxies(input_item, secrets.get("proxy_password")),
            "skey": secrets.get("skey"),
        }

        if input_item.get("duo_security_logs"):
            config["duo_security_logs"] = input_item.get("duo_security_logs")

        return config

    @staticmethod
    def get_proxies(input_item: dict, decoded_password: str) -> dict:
        """
        Retrieves proxy settings based on the given input item and decoded password.

        :param input_item: A dictionary containing proxy configuration details
        :param decoded_password: The decoded password for authentication.

        :return: dict: A dictionary with proxy settings if available, otherwise None.
        """
        if solnlib_utils.is_true(str(input_item.get("proxy_enabled"))):
            # Retrieve proxy related fields
            proxy_username = input_item.get("proxy_username", None)
            proxy_password = decoded_password
            proxy_url = input_item.get("proxy_url", None)
            proxy_port = input_item.get("proxy_port", None)
            proxy_type = 'CONNECT'

            if proxy_username and proxy_password:
                # If auth options provided
                LOGGER.info("Proxy enabled with authentication")
                proxy_auth = f"{proxy_username}:{proxy_password}"
                headers = {
                    "Proxy-Authorization":
                        "Basic " + base64.b64encode(proxy_auth.encode()).decode()
                }
                proxies = {
                    "proxy_headers": headers,
                    "proxy_host": proxy_url,
                    "proxy_port": proxy_port,
                    "proxy_type": proxy_type
                }
            else:
                # If no auth options
                LOGGER.info("Proxy enabled without authentication")
                proxies = {
                    "proxy_host": proxy_url,
                    "proxy_port": proxy_port,
                    "proxy_type": proxy_type
                }
        else:
            LOGGER.info("Proxy not enabled")
            proxies = None

        return proxies

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter) -> None:
        """The method called to stream events into Splunk.
        It should do all its output through an EventWriter,
        which writes events and error messages from the module input.

        :param inputs: An ``InputDefinition`` object.
        :param ew: An object with methods to write events and log messages to Splunk.
        """
        for input_name, input_item in inputs.inputs.items():
            LOGGER.info("Getting input configuration.")
            normalized_input_name = input_name.split("/")[-1]

            session_key = self._input_definition.metadata["session_key"]

            config = self.prepare_config(input_name, input_item, session_key)

            LOGGER.info(
                "Configuration processing completed. "
                f"Setting LOGGER level for {normalized_input_name} to "
                f"{config['logging_level']}"
            )
            LOGGER.setLevel(config["logging_level"])

            splunk_session_args = {
                "token": session_key,
                "user": "nobody",
                "app": APP_NAME,
            }

            local_mode: bool = config.get("api_host") == LOCAL_API_HOST

            admin_api = duo_client.Admin(
                ikey=config.get("ikey"),
                skey=config.get("skey"),
                host=config.get("api_host"),
                ca_certs="DISABLE" if local_mode else None,
                digestmod=hashlib.sha512,
            )
            # Use proxy if needed
            proxies = config.get("proxies")
            if proxies:
                admin_api.set_proxy(
                    host=proxies["proxy_host"],
                    port=proxies["proxy_port"],
                    headers=proxies.get("proxy_headers"),
                    proxy_type=proxies["proxy_type"]
                )
            # Why not just let the log class define the endpoint name?
            # Look into why this was needed
            timestamp_path = os.path.dirname(os.path.abspath(__file__))
            exception = error_type = None
            possible_failure_reason = ""
            log_name = ""
            try:
                for logclass in LOG_CLASSES:
                    log_name: str = logclass.__name__

                    log_name = self._log_attribute_name(
                        logclass.__name__.replace("Paginated", "")
                    )
                    # Check if logs should be pulled for a "logclass"
                    # based on configuration setting
                    if log_name in config.get("duo_security_logs"):
                        LOGGER.info(f"Starting collector for {logclass.__name__}")
                        log = logclass(
                            admin_api, timestamp_path,
                            splunk_session_args, config, ew
                        )
                        log.run()

                        LOGGER.info(f"Ending execution for {normalized_input_name}.")
                        LOGGER_STATUS.info(
                            f"instance={normalized_input_name}, "
                            "product=Duo, "
                            "filter_value=sbg_duo_input.py, "
                            "status=Connected"
                        )
            except KVStoreTimeoutError as kte:
                exception = kte
                error_type = "KVStoreTimeoutError"
                possible_failure_reason = "KVStore has failed to start"
            except (RuntimeError, MaxRequestAttemptsReached) as ex:
                exception = ex
                error_type = "Throttling"
            except Exception as ex:
                exception = ex
                error_type = "Uncategorized"
            finally:
                if exception:
                    LOGGER_ERROR.error(
                        f"instance={normalized_input_name}, "
                        f"error_type={error_type}, "
                        f"error_code={type(exception).__name__}, "
                        f"error_detail=Unable to process {log_name} logs, "
                        f"filter_value=sbg_duo_input.py, "
                        f"traceback={exception},"
                    )
                    LOGGER_STATUS.info(
                        f"instance={normalized_input_name}, "
                        f"error_type={error_type}, "
                        "product=DUO, "
                        "filter_value=sbg_duo_input.py, "
                        f"error_code={type(exception).__name__}, "
                        f"possible_failure_reason={possible_failure_reason}, "
                        "status=Not Connected,"
                    )

    def _log_attribute_name(self, log_class_name: str) -> str:
        """
        Convert log class name into Splunk attribute name

        :param log_class_name: The name of the log class to be converted.

        :return: str: The corresponding Splunk attribute name.
        """
        new_string = []
        for i in range(1, len(log_class_name)):
            if (
                    log_class_name[i] in string.ascii_lowercase
                    or log_class_name[i] in string.digits
            ):
                new_string.append(log_class_name[i])
            elif log_class_name[i] in string.ascii_uppercase:
                new_string.append("_")
                new_string.append(log_class_name[i].lower())
        attribute_string = log_class_name[0].lower()
        attribute_string += "".join(new_string)
        return attribute_string


if __name__ == "__main__":
    exit_code = SBGDuoInput().run(sys.argv)  # pragma: no cover
    sys.exit(exit_code)  # pragma: no cover
