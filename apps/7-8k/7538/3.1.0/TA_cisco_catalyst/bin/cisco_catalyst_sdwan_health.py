"""Modular input for SDWAN Health."""

import import_declare_test  # noqa: F401 isort: skip
import concurrent.futures
import sys

import cisco_catalyst_exceptions as cce
import consts
import logger_manager
import sdwan.sdwan_utils as sdwan_utils
import utils
from splunklib import modularinput as smi


class SDWANHealth(smi.Script):
    """Get the Health Details from Cisco SDWAN Server."""

    def __init__(self):
        """Initialise SDWANHealth class."""
        super(SDWANHealth, self).__init__()

    def get_scheme(self):
        """Load the arguments in the Configuration page."""
        scheme = smi.Scheme("cisco_catalyst_sdwan_health")
        scheme.description = "Go to the add-on's configuration UI and configure modular inputs under the Inputs menu."
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
                "sdwan_account",
                title="SDWAN Account",
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "health_type",
                title="Health Type",
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "logging_level",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        """Validate the input parameters provided by the user."""
        sdwan_account = definition.parameters.get("sdwan_account")
        if not sdwan_account:
            msg = "SDWAN Account not found. Please add a valid account."
            raise ValueError(msg)

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        """Collect the data from the Cisco SDWAN Server."""
        try:
            session_key = self._input_definition.metadata["session_key"]
            input_name, input_conf = [
                [key.split("/")[-1], val] for key, val in inputs.inputs.items()
            ][0]
            input_conf["input_name"] = input_name
            input_conf["input_stanza_name"] = "".join(
                ["cisco_catalyst_sdwan_health://", input_name]
            )
            logger = logger_manager.get_logger(
                f"sdwan_health_{input_name}", input_conf["logging_level"]
            )
            logger.info("Starting data collection for input - {}".format(input_name))

            health_type_list = [
                item.strip() for item in input_conf.get("health_type").split(",")
            ]
            logger.info(f"Collecting data for health types - {health_type_list}")

            sdwan_account = input_conf.get("sdwan_account")
            if not sdwan_account:
                raise cce.SDWANInvalidGlobalAccount(
                    "Invalid sdwan_account for input '{}'.".format(input_name)
                )

            # Getting account details
            account_conf = utils.get_account_config(
                session_key, consts.SDWAN_ACCOUNT_CONF_FILE, logger
            )
            account_conf_info = account_conf.get(sdwan_account)

            hostname = account_conf_info.get("hostname")
            username = account_conf_info.get("username")
            password = account_conf_info.get("password")

            config = sdwan_utils.SDWANConfig(session_key, account_conf_info, logger)
            verify_ssl = config.get_verify_ssl_cert()

            # Getting proxy settings
            proxy_settings = config.get_proxy_settings()
            if proxy_settings:
                logger.info("Proxy has been set, using proxy details for data collection of input '{}'".format(
                    input_name
                ))
            else:
                logger.info("Proxy not set, using default settings for data collection of input '{}'".format(
                    input_name
                ))

            authenticate = sdwan_utils.Authentication(
                logger,
                hostname,
                username,
                password,
                proxy_settings,
                verify_ssl,
            )
            jsession_id, token = authenticate.get_token()
            if token and jsession_id:
                self.headers = {
                    "X-XSRF-TOKEN": token,
                    "Accept": "application/json",
                    "Cookie": jsession_id,
                }
                logger.info(
                    f"instance={input_name}, "
                    "product=Cisco SDWAN, "
                    f"filter_value={input_conf['input_stanza_name']}, "
                    "status=Connected,"
                )
            else:
                logger.info(
                    f"instance={input_name}, "
                    "error_type=Authentication Error"
                    "product=Cisco SDWAN, "
                    f"filter_value={input_conf['input_stanza_name']}, "
                    "status=Not Connected,"
                )
                raise cce.AuthenticationError(
                    "Authentication Error. Failed to get token for data collection."
                )

            # get device ids list
            device_ids = []
            device_manager = sdwan_utils.DeviceManager(
                hostname,
                token,
                jsession_id,
                logger,
                verify_ssl,
                input_conf,
                event_writer,
                proxy_settings,
            )
            device_ids = device_manager.get_device_ids()

            health_data_collector = sdwan_utils.HealthDataCollector(
                hostname,
                self.headers,
                verify_ssl,
                logger,
                input_conf,
                event_writer,
                proxy_settings,
            )

            future_obj = []
            total_event_count = 0
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=consts.SDWAN_MAX_WORKERS,
            ) as executor:
                for device_id in device_ids:
                    future_obj.append(
                        executor.submit(
                            sdwan_utils.get_health_data,
                            health_data_collector,
                            device_id,
                            health_type_list,
                        )
                    )
            for future in concurrent.futures.as_completed(future_obj):
                try:
                    future_dict = future.result()
                    total_event_count += future_dict["event_count"]
                except Exception as e:
                    logger.exception(f"Error occurred while processing future: {e}")

            logger.info(
                f"Total health events ingested = {total_event_count} for health types = {health_type_list}\n"
                f"End of data collection for input_name={input_name}"
            )

        except Exception as e:
            logger.exception(
                "Cisco Catalyst SDWAN Error: while collecting {} data: {}".format(
                    health_type_list, e
                )
            )


if __name__ == "__main__":
    exit_code = SDWANHealth().run(sys.argv)
    sys.exit(exit_code)
