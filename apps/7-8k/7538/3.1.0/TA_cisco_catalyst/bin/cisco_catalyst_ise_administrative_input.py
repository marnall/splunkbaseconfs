"""Modular input for ISE Input."""

import import_declare_test  # noqa: F401
import concurrent.futures
import sys

import requests

import cisco_catalyst_exceptions as cce
import consts
import ise.ise as ise
import ise.ise_utils as ise_utils
import ise.pxgrid_api_helper as pxapi
import logger_manager
import utils
from solnlib.utils import is_true
from splunklib import modularinput as smi

ISE_DATA_COLLECTION_ERROR = (
    "Cisco Catalyst ISE Error: while collecting data for '{}'. Error:{}"
)
ISE_DATA_COLLECTION_TERMINATION = (
    "Cisco Catalyst ISE Error: failed to complete data collection and terminated."
)
ISE_DATA_COLLECTION_TIMEOUT_ERROR = (
    "Cisco Catalyst ISE Error: Timed out while collecting data for '{}'."
)


class ISEInput(smi.Script):
    """Get the Health Details from Cisco ISE Server."""

    def __init__(self):
        """Initialise ISEInput class."""
        super(ISEInput, self).__init__()

    def get_scheme(self):
        """Load the arguments in the Configuration page."""
        scheme = smi.Scheme("cisco_catalyst_ise_administrative_input")
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
                "ise_account",
                title="ISE Account",
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "data_type",
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

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        """Collect the data from the Cisco ISE Server."""
        try:
            session_key = self._input_definition.metadata["session_key"]
            ew = event_writer
            input_name, input_conf = [
                [key.split("/")[-1], val] for key, val in inputs.inputs.items()
            ][0]
            input_conf["input_name"] = input_name
            input_conf["session_key"] = session_key
            input_conf["input_stanza_name"] = "".join(
                ["cisco_catalyst_ise_administrative_input://", input_name]
            )
            logger = logger_manager.get_logger(
                f"ise_administrative_{input_name}", input_conf["logging_level"]
            )
            logger.info("Data collection started for input: '{}'".format(input_name))

            if not input_conf.get("data_type"):
                logger.error(
                    f"No Data types found in the input: '{input_name}'. Please select data types to collect data."
                )
                return
            data_type_list = [x.strip() for x in input_conf.get("data_type").split(",")]
            logger.info(f"Collecting data for data types - {data_type_list}")
            ise_account = input_conf.get("ise_account")

            if not ise_account:
                raise cce.ISEInvalidGlobalAccount(
                    "Invalid ise_account for input '{}'.".format(input_name)
                )

            # Getting account details
            account_conf = utils.get_account_config(
                session_key, consts.ISE_ACCOUNT_CONF_FILE, logger
            )
            account_conf_info = account_conf.get(ise_account)
            hostname = account_conf_info.get("hostname").strip("").strip("/")
            username = account_conf_info.get("username")
            password = account_conf_info.get("password")
            pxgrid_host = account_conf_info.get("pxgrid_host")
            pxgrid_client_username = account_conf_info.get("pxgrid_client_username")
            pxgrid_client_password = account_conf_info.get("pxgrid_client_password")
            pxgrid_cert_auth = account_conf_info.get("pxgrid_cert_auth")
            headers = utils.make_headers(username, password)
            config = utils.Config(session_key, account_conf_info, logger)
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
            future_obj = []
            total_event_count = 0

            # Test Connectivity to ISE Server
            try:
                url = "".join([hostname, consts.ISE_AUTH_ENDPOINT])
                ise_client = ise.CiscoISE(logger, proxy_settings, verify_ssl)
                response = ise_client.get_ise_response(
                    url=url,
                    headers=headers,
                )
                response.raise_for_status()
                logger.info(
                    f"instance={input_name}, "
                    "product=Cisco ISE, "
                    f"filter_value=cisco_catalyst_ise_administrative_input://{input_name}, "
                    "status=Connected,"
                )
            except requests.exceptions.HTTPError as e:
                logger.error(
                    f"Error while connecting to ISE server: {e}"
                )
                logger.info(
                    f"instance={input_name}, "
                    "error_type=Configuration, "
                    "product=Cisco ISE, "
                    f"filter_value=cisco_catalyst_ise_administrative_input://{input_name}, "
                    "status=Not Connected,"
                )
                raise cce.AuthenticationError(
                    "Failed to connect to ISE server for data collection."
                )
            except Exception as e:
                logger.error(
                    f"Error while connecting to ISE server: {e}"
                )
                logger.error(
                    f"instance={input_name}, "
                    "error_type=Configuration, "
                    "product=Cisco ISE, "
                    f"filter_value=cisco_catalyst_ise_administrative_input://{input_name}, "
                    "status=Not Connected,"
                )
                raise cce.AuthenticationError(
                    "Failed to connect to ISE server for data collection."
                )

            kwargs = {
                "hostname": hostname,
                "headers": headers,
                "verify_ssl": verify_ssl,
                "logger": logger,
                "input_conf": input_conf,
                "ew": ew,
                "proxy": proxy_settings,
            }

            # Initialize and collect data for inputs which require threading
            cert = None
            if is_true(pxgrid_cert_auth):
                cert = consts.ISE_CLIENT_CERT_FILE_LOC.format(
                    cert_name=account_conf_info.get("copy_account_name").strip()
                )
            data_collectors = {
                "security_group_tags": ise_utils.SecurityGroupsDataCollector(
                    session_key=session_key, **kwargs
                ).get_data,
                "ip_sgt_bindings": pxapi.CiscopxGrid(
                    pxgrid_host=pxgrid_host,
                    pxgrid_client_username=pxgrid_client_username,
                    pxgrid_client_password=pxgrid_client_password,
                    cert=cert,
                    **kwargs
                ).get_data,
                "authz_policy_hit": ise_utils.AuthPolicyDataCollector(**kwargs).get_data,
                "ise_tacacs_rule_hit": ise_utils.DevicePolicyDataCollector(**kwargs).get_data,
            }

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=consts.ISE_MAX_WORKERS,
            ) as executor:
                for data_type in data_type_list:
                    future_obj.append(executor.submit(data_collectors[data_type]))

            for future in concurrent.futures.as_completed(future_obj):
                try:
                    data_collection_results = future.result()
                    logger.info(
                        f"Ingested {data_collection_results['event_count']} event(s) "
                        f"for data_type={data_collection_results['data_type']}"
                    )
                    total_event_count += data_collection_results["event_count"]
                except Exception as e:
                    logger.exception(f"Error occurred while processing future: {e}")

            logger.info(
                f"Data collection completed for input: '{input_name}'. "
                f"Total ingested events: {total_event_count} for data types={data_type_list}"
            )
        except concurrent.futures.TimeoutError:
            logger.error(ISE_DATA_COLLECTION_TIMEOUT_ERROR.format(data_type_list))
            logger.error(ISE_DATA_COLLECTION_TERMINATION)
        except Exception as e:
            logger.error(ISE_DATA_COLLECTION_ERROR.format(data_type_list, e))
            logger.error(ISE_DATA_COLLECTION_TERMINATION)


if __name__ == "__main__":
    exit_code = ISEInput().run(sys.argv)
    sys.exit(exit_code)
