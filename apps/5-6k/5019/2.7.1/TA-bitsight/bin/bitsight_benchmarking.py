import import_declare_test  # noqa F401

import os
import json
import sys
import traceback
import time
import datetime
from base64 import b64encode
import urllib.parse as urllib

from splunklib import modularinput as smi

from conf_helper import get_conf_file
from setup_logger import setup_logging
from bitsight_utils import BitsightCompanyGuidMapper, raise_webmessage
from bitsight_constants import ENDPOINT_DISPATHCER

logger = setup_logging("ta_bitsight_bitsight_benchmarking")


class BitsightBenchmarking(smi.Script):
    """Class for modular input."""

    def __init__(self):
        """Initialize the BitsightBenchmarking Class."""
        self.global_checkbox_fields = None
        super(BitsightBenchmarking, self).__init__()

    def get_scheme(self):
        """Overloaded splunklib modularinput method."""
        scheme = smi.Scheme('Bitsight Benchmarking')
        scheme.description = (
            "Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu."
        )
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )
        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
        scheme.add_argument(
            smi.Argument(
                'start_date',
                title='Start Date',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'company_tree_multiselect',
                title='Companies',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'skip_checkpoint',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'edit_flag',
                required_on_create=False,
            )
        )
        return scheme

    def get_app_name(self):
        """Method to get App name."""
        return "TA-bitsight"

    def validate_input(self, definition: smi.ValidationDefinition):
        """Validate the input stanza."""
        pass

    def get_account_fields(self):
        """Get account fields."""
        account_fields = []
        return account_fields

    def get_checkbox_fields(self):
        """Get checkbox fields."""
        checkbox_fields = []
        return checkbox_fields

    def get_global_checkbox_fields(self):
        """Get global checkbox fields."""
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(
                bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error(
                    'Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields

    def _get_mapping(self):
        return self.bsobject.get_map()

    def _create_selected_companies_map(self):
        scmap_list = []
        if 'All' in self.selected_companies:
            self.selected_companies = [each['company_name'] for each in self.companies_map]
        for company in self.selected_companies:
            temp = {'company_name': company, 'company_guid': next(
                item['_key'] for item in self.companies_map if item["company_name"] == company)}
            scmap_list.append(temp)
            temp = {}
        return scmap_list

    def engine(self, input_name, input_item, meta_configs, ew):
        """
        Bitsight data collection engine.

        :param ew: Splunk Event Writer object.
        """
        logger.info("Data collection started for <{}>".format(input_name))
        api = self.api_token + ':' + self.api_token
        user_and_pass = b64encode(api.encode()).decode("ascii")
        auth_header = 'Basic {}'.format(user_and_pass)
        params = {
            'meta_configs': meta_configs,
            'input_name': input_name,
            'input_item': input_item,
            'session_key': self.session_key,
            'logger': logger,
            'event_writer': ew,
            'base_url': self.base_url,
            'api_token': self.api_token,
            'auth_header': auth_header
        }
        for company in self.selected_companies_map:
            logger.info('starting data collection for {}'.format(company.get('company_name')))
            for endpoint_name, dispatcher_map in ENDPOINT_DISPATHCER.items():
                if endpoint_name in (
                    'companies',
                    'graph_data',
                    'findings',
                    'diligence_statistics',
                    'observations_statistics'
                ):
                    params['endpoint_name'] = endpoint_name
                    params['endpoint_url'] = dispatcher_map.get('url')
                    params['company_name'] = company['company_name']
                    params['company_guid'] = company['company_guid']
                    params['is_benchmarking'] = "True"
                    dispatcher_map['function'](params)

    def _validate_interval(self, input_item):
        """Validate the interval parameter."""
        try:
            interval = int(input_item.get('interval'))
            if interval < 300 or interval > 14515200:
                logger.error("Interval value should be between 300 to 14515200 seconds.")
                return False
            return True
        except (ValueError, SyntaxError, TypeError) as e:
            if isinstance(e, ValueError):
                logger.error(f'Invalid value "{input_item.get("interval")}" of parameter "Interval".')
            elif isinstance(e, SyntaxError):  # SyntaxError will be raised in case of empty value
                logger.error('Interval field is not provided.')
            else:  # TypeError will be raised if key will not found in the conf
                logger.error('Unable to find value of parameter "Interval".')
            return False

    def _validate_start_date(self, input_item):
        """Validate the start date parameter."""
        provided_date = input_item.get("start_date", "").strip()
        if not provided_date:
            logger.error("Start Date is not Provided")
            return False

        try:
            formatted_start_date = datetime.datetime.strptime(provided_date, "%Y-%m-%d")
            if formatted_start_date >= datetime.datetime.now():
                logger.error("Cannot fetch data from the future. Please enter an appropriate Start Date.")
                return False
            return True
        except ValueError:
            logger.error("Start Date must be in the format YYYY-MM-DD.")
            return False

    def _validate_companies(self, input_item):
        """Validate the companies parameter."""
        companies = input_item.get("company_tree_multiselect")
        if not companies:
            logger.error("Companies are not Provided")
            return False
        return True

    def _load_configuration(self, input_item, meta_configs):
        """Load and validate configuration settings."""
        self.session_key = meta_configs['session_key']
        self.server_uri = meta_configs['server_uri']

        # Initialize company mapping
        self.bsobject = BitsightCompanyGuidMapper(self.session_key, "benchmarking")
        self.companies_map = self._get_mapping()
        self.endpoint_map = {}
        self.selected_companies = input_item.get("company_tree_multiselect").split('|')
        self.selected_companies_map = self._create_selected_companies_map()

        # Initialize API settings
        self.base_url = ''
        self.api_param = ''
        self.api_token = ''
        logger.debug("Global variables set.")

        # Load and validate Splunk REST host info
        splunk_rest_host_info = get_conf_file(
            file="ta_bitsight_settings",
            session_key=self.session_key,
            stanza="authentication"
        )

        # Process API URL
        url = splunk_rest_host_info.get('api_url')
        if url:
            url_prefix = url.split(":")
            if url_prefix[0] == "http":
                url = url.replace("http", "https")
            elif url_prefix[0] == "https":
                logger.debug("Url is valid.")
            else:
                logger.info("Invalid URL. Using default URL for further processing.")
                url = 'https://api.bitsighttech.com/'
        self.base_url = url or 'https://api.bitsighttech.com/'

        # Validate API token
        api_token = splunk_rest_host_info.get('bitsight_api_token')
        if not api_token:
            logger.info("Please Add BitSight API-Token, Goto --> Configuration--> Add-onSettings")
            raise_webmessage(meta_configs, response=2)
            return False

        self.api_token = api_token
        self.api_param = f"{api_token}:{api_token}"

        # Validate server URI
        try:
            http_info = urllib.urlparse(self.server_uri)
            if not all([http_info.scheme, http_info.hostname, http_info.port]):
                raise ValueError("Invalid server URI format")
        except Exception:
            logger.error(f"{self.server_uri} is not in http(s)://hostname:port format")
            return False

        return True

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        """Stream events with improved structure and reduced complexity."""
        try:
            start_time = time.time()

            for name, item in inputs.inputs.items():
                input_name = name.split('://')[1]
                input_item = item

                # Validate input parameters
                if not all([
                    self._validate_interval(input_item),
                    self._validate_start_date(input_item),
                    self._validate_companies(input_item)
                ]):
                    return False

                # Load and validate configuration
                meta_configs = self._input_definition.metadata
                if not self._load_configuration(input_item, meta_configs):
                    return False

                # Process the data
                self.engine(input_name, input_item, meta_configs, ew)

                # Log completion
                total_time = time.time() - start_time
                logger.info(f"Data Indexed Successfully for all endpoints. Total time taken: {total_time:.2f} seconds")
                return True

        except Exception as e:
            logger.error(f"Error in stream_events: {str(e)}")
            logger.error(traceback.format_exc())
            return False


if __name__ == '__main__':
    exit_code = BitsightBenchmarking().run(sys.argv)
    sys.exit(exit_code)
