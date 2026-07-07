import import_declare_test
import sys
import time
import traceback

from silent_push_helpers.logger_manager import setup_logging
from silent_push_helpers.rest_helper import RestHelper
from silent_push_helpers.conf_helper import get_credentials
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option
from silent_push_helpers.utils import check_indicator_type

logger = setup_logging("ta_silent_push_threat_check_custom_command")

REDIRECT_TO_LOG_FILE_MSG = "See {} for more details.".format(
    "ta_silent_push_threat_check_custom_command.log"
)
DATA_TYPE = "iofa"


@Configuration()
class SilentPushThreatCheckCommand(EventingCommand):
    """SilentPushThreatCheckCommand Class."""

    account_name = Option(name="account_name", require=True)
    data_source = Option(name="data_source", require=True)
    indicators = Option(name="indicators", require=False)
    index_field = Option(name="index_field", require=False)
    datamodel_field = Option(name="datamodel_field", require=False)

    all_indicators = {"domains": [], "ips": []}

    def _write_error(self, msg):
        """Log error message to Splunk UI from where this custom command was triggered."""
        self.write_error("{} {}".format(msg, REDIRECT_TO_LOG_FILE_MSG))
        exit(0)

    def _process_indicator(self, query):
        """Process a single indicator and return threat check response."""
        query = query.strip()
        indicator_type = check_indicator_type(query)

        if indicator_type == "domain":
            return self._get_threat_check_response("name", query, "domain")
        elif indicator_type in ["ipv4", "ipv6"]:
            return self._get_threat_check_response("ip", query, "ip")
        else:
            logger.warning(
                f"message=invalid_indicator | Not a valid indicator: {query} for type ip or domain"
            )
            return None

    def _get_threat_check_response(self, api_type, query, indicator_type):
        """Get threat check response from Silent Push API."""
        response_threat_check = self.rest_helper_obj.indicator_present_on_silent_push(
            api_type, query, self.silent_push_threat_check_api
        )
        response_threat_check.update({"indicator_type": indicator_type})
        return response_threat_check

    def _add_to_indicators(self, response):
        """Add response to appropriate indicators list."""
        if response is None:
            return

        indicator_type = response.get("indicator_type")
        if indicator_type == "domain":
            self.all_indicators["domains"].append(response)
        elif indicator_type == "ip":
            self.all_indicators["ips"].append(response)

    def _process_indicators_list(self):
        """Process indicators from comma-separated list."""
        if not self.indicators:
            return

        indicators_list = self.indicators.split(",")
        for indicator in indicators_list:
            response = self._process_indicator(indicator)
            self._add_to_indicators(response)

    def _process_events(self, events, field_name):
        """Process events from index or datamodel source."""
        for event in events:
            field_value = event.get(field_name, "")
            if field_value:
                response = self._process_indicator(field_value)
                self._add_to_indicators(response)

    def _yield_results(self):
        """Yield all collected indicators as results."""
        current_time = time.time()

        for indicator in self.all_indicators["domains"]:
            yield {"_raw": indicator, "_time": current_time}

        for indicator in self.all_indicators["ips"]:
            yield {"_raw": indicator, "_time": current_time}

    def transform(self, events):
        """Transform method."""
        try:
            logger.info(
                "message=command_start_execution | Started Custom Command Script Execution."
            )
            start_time = time.time()

            # Initialize configuration and API client
            self._initialize_api_client()

            # Process indicators based on data source
            self._process_data_source(events)

            logger.info(
                "message=command_info | Successfully executed threat check API."
            )

            # Yield results
            yield from self._yield_results()

            # Log completion
            end_time = time.time()
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, end_time - start_time
                )
            )

        except Exception as ex:
            logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self._write_error("Unknown Error: {}".format(ex))

    def _initialize_api_client(self):
        """Initialize Silent Push API client configuration."""
        session_key = self._metadata.searchinfo.session_key
        silent_push_config = {"session_key": session_key}
        account_info = get_credentials(self.account_name, session_key)
        silent_push_config.update(account_info)

        self.rest_helper_obj = RestHelper(silent_push_config, logger)
        self.silent_push_threat_check_api = account_info.get("threat_check_api_key", "")

    def _process_data_source(self, events):
        """Process indicators based on the specified data source."""
        if self.data_source == "indicators":
            self._process_indicators_list()
        elif self.data_source == "index":
            self._process_events(events, self.index_field)
        elif self.data_source == "datamodel":
            self._process_events(events, self.datamodel_field)
        else:
            logger.error("message=command_error | Invalid data source.")


dispatch(SilentPushThreatCheckCommand, sys.argv, sys.stdin, sys.stdout, __name__)
