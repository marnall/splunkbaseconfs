"""Modular input for Cyber Vision Flows."""
import import_declare_test  # noqa: F401

import sys
import time
import calendar
import datetime
import re

import consts
import utils
import splunk.version as ver
from splunklib import modularinput as smi
import logger_manager
import cisco_catalyst_exceptions as cce

CONNECTED_LOG = (
    "instance={}, product=Cisco Cyber Vision, "
    "filter_value=cisco_catalyst_cybervision_flows://{}, status=Connected,"
)
NOT_CONNECTED_LOG = (
    "instance={}, product=Cisco Cyber Vision, "
    "filter_value=cisco_catalyst_cybervision_flows://{}, status=Not Connected,"
)


class CiscoCyberVisionFlows(smi.Script):
    """Get the Flow details from Cisco CyberVision Server."""

    def __init__(self):
        """Initialise CiscoCyberVisionFlows class."""
        super(CiscoCyberVisionFlows, self).__init__()

    def get_scheme(self):
        """Load the arguments in the Configuration page."""
        scheme = smi.Scheme('cisco_catalyst_cybervision_flows')
        scheme.description = (
            "Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu."
        )
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name",
                title="Name",
                required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "cyber_vision_account",
                title="Cyber Vision Account",
                required_on_create=True,
                required_on_edit=False
            )
        )
        scheme.add_argument(
            smi.Argument(
                "start_date",
                title="Start Date",
                required_on_create=True,
                required_on_edit=False
            )
        )

        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        """Validate the input parameters provided by the user."""
        cyber_vision_account = definition.parameters.get('cyber_vision_account')
        if not cyber_vision_account:
            msg = "Cyber Vision Account not found. Please add a valid account."
            raise ValueError(msg)

        start_date = definition.parameters.get('start_date')
        if start_date:
            if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", start_date):
                msg = 'Start date should be in "YYYY-MM-DDThh:mm:ssZ" format.'
                raise ValueError(msg)

            # Convert start_date string to epoch time
            time_pattern = "%Y-%m-%dT%H:%M:%SZ"
            start_date_epoch = calendar.timegm(time.strptime(start_date, time_pattern))

            # Validate start_date is valid
            current_utc = calendar.timegm(datetime.datetime.utcnow().timetuple())
            if start_date_epoch < 0:
                msg = 'Start date can not be lesser than "1970-01-01T00:00:00Z".'
                raise ValueError(msg)

            if start_date_epoch > current_utc:
                msg = 'Start date can not be greater than current UTC.'
                raise ValueError(msg)

    def get_verify_ssl_cert(self, session_key, account_conf_info, logger):
        """Get verify ssl settings."""
        use_ca_cert = account_conf_info.get("use_ca_cert")
        verify_ssl = True
        if utils.is_true(use_ca_cert):
            verify_ssl = consts.CYBER_VISION_CERT_FILE_LOC.format(
                cert_name=account_conf_info.get("copy_account_name").strip()
            )
        else:
            verify_ssl = utils.get_verify_ssl(session_key, logger)
        return verify_ssl

    def get_proxy_settings(self, account_conf_info):
        """Get proxy settings."""
        proxy_settings = None
        if utils.is_true(account_conf_info.get("enable_proxy")):
            proxy_username = account_conf_info.get('proxy_username', '')
            proxy_password = account_conf_info.get('proxy_password', '')
            proxy_type = account_conf_info.get('proxy_type')
            proxy_url = account_conf_info.get('proxy_url')
            proxy_port = account_conf_info.get('proxy_port')
            proxy_uri = utils.get_proxy_uri(
                proxy_username, proxy_password, proxy_type, proxy_url, proxy_port
            )
            proxy_settings = {"http": proxy_uri, "https": proxy_uri}
        return proxy_settings

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        """Collect the data from the Cisco CyberVision Server."""
        try:
            session_key = self._input_definition.metadata["session_key"]
            input_name, input_conf = [[key.split("/")[-1], val] for key, val in inputs.inputs.items()][0]
            input_conf["input_name"] = input_name
            dc_starting_time = datetime.datetime.now()
            logger = logger_manager.get_logger(
                f"cybervision_flows_{input_name}", input_conf["logging_level"]
            )
            logger.info("Starting data collection for input {} at {}".format(input_name, dc_starting_time))

            cyber_vision_account = input_conf.get('cyber_vision_account')
            if not cyber_vision_account:
                raise cce.CyberVisionInvalidGlobalAccount(
                    "Invalid cyber_vision_account for input '{}'.".format(input_name)
                )

            # Getting account details
            account_conf = utils.get_account_config(session_key, consts.CYBERVIVSION_ACCOUNT_CONF_FILE, logger)
            account_conf_info = account_conf.get(cyber_vision_account)

            api_token = account_conf_info.get('api_token')
            server_address = account_conf_info.get('ip_address')
            page_size = input_conf.get('page_size')
            verify_ssl = self.get_verify_ssl_cert(session_key, account_conf_info, logger)
            stanza_name = str(input_name)
            current_time = int(time.time() * 1000)
            splunk_version = ver.__version__
            if not splunk_version:
                logger.error("Cisco Cyber Vision Error: unable to fetch splunk version.")
                return

            # Getting proxy settings
            proxy_settings = self.get_proxy_settings(account_conf_info)
            if proxy_settings:
                logger.info("Proxy has been set, using proxy details for data collection of input '{}'".format(
                    input_name
                ))
            else:
                logger.info("Proxy not set, using default settings for data collection of input '{}'".format(
                    input_name
                ))

            # Storing necessary data into dictionary
            config_details = {}
            config_details['server_address'] = server_address
            if not server_address.startswith("https"):
                error_msg = (
                    "Unsuccessfully terminating the data collection. "
                    "Reason: Server address should start with https. Found {}"
                ).format(server_address)
                logger.error(error_msg)
                raise cce.CyberVisionInvalidServerAddress(error_msg)

            host_name = server_address.split("https://")[1]
            config_details.update({
                'user_agent': "Splunk/{}".format(splunk_version),
                'stanza': stanza_name,
                'proxy_settings': proxy_settings,
                'verify_ssl': verify_ssl,
                'api_token': api_token,
                'api_version': "3.0",
                'end_date': current_time
            })
            sourcetype = "cisco:cybervision:flows"
            endpoint = "/flows"
            config_details['checkpoint_name'] = utils.get_cybervision_checkpoint_name(
                config_details, sourcetype, endpoint
            )
            checkpoint_value = utils.get_checkpoint(
                session_key,
                config_details['checkpoint_name'],
                logger,
                consts.CYBERVISION_COLLECTION_NAME
            )
            config_details['start_date'] = utils.get_cybervision_startdate(
                input_conf, config_details, checkpoint_value, logger
            )
            start_date = config_details['start_date']
            page = 1

            while True:
                params = {
                    "from": start_date,
                    "to": current_time,
                    "sort": "lastActivity:desc",
                    "page": page,
                    "size": page_size
                }
                data = utils.cybervision_request_get("flows", config_details, params)

                if data and (page == 1):
                    last_activity = data[0]['lastActivity']
                    config_details['end_date'] = last_activity + 1
                page += 1
                additional_fields = {"host": host_name, "time_field": "lastActivity"}
                utils.cybervision_ingest_in_splunk(
                    input_conf,
                    ew,
                    data,
                    sourcetype,
                    additional_fields,
                    source="Flows"
                )
                if len(data) < int(page_size):
                    break

            utils.update_checkpoint(
                session_key,
                config_details['checkpoint_name'],
                config_details['end_date'],
                logger,
                consts.CYBERVISION_COLLECTION_NAME
            )
            logger.info(CONNECTED_LOG.format(input_name, input_name))
            logger.info("Data collection process is completed for input {}".format(input_name))
            logger.info("Total time taken in data collection for input {} is {} seconds".format(
                input_name, (datetime.datetime.now() - dc_starting_time).total_seconds()))
        except cce.CyberVisionInvalidGlobalAccount as e:
            logger.info(NOT_CONNECTED_LOG.format(input_name, input_name))
            logger.error(utils.DATA_COLLECTION_ERROR.format("Flows", e))
            logger.error(utils.DATA_COLLECTION_TERMINATION)
        except cce.CyberVisionInvalidServerAddress as e:
            logger.info(NOT_CONNECTED_LOG.format(input_name, input_name))
            logger.error(utils.DATA_COLLECTION_ERROR.format("Flows", e))
            logger.error(utils.DATA_COLLECTION_TERMINATION)
        except cce.CyberVisionInvalidStartDate as e:
            logger.info(NOT_CONNECTED_LOG.format(input_name, input_name))
            logger.error(utils.DATA_COLLECTION_ERROR.format("Flows", e))
            logger.error(utils.DATA_COLLECTION_TERMINATION)
        except Exception as e:
            logger.info(NOT_CONNECTED_LOG.format(input_name, input_name))
            logger.error(utils.DATA_COLLECTION_ERROR.format("Flows", e))
            logger.error(utils.DATA_COLLECTION_TERMINATION)


if __name__ == '__main__':
    exit_code = CiscoCyberVisionFlows().run(sys.argv)
    sys.exit(exit_code)
