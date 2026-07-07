import import_declare_test
import os
import sys
import time
import traceback
import json
import requests
from datetime import datetime
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import splunklib.client as client
import splunklib.results as results

from infoblox_helpers.kvstore import CollectionManager
from infoblox_helpers.logger_manager import setup_logging
from infoblox_helpers.conf_helper import get_credentials
from infoblox_helpers.rest_helper import RestHelper


logger = setup_logging("ta_infoblox_soc_insights_details_custom_command")

INFOBLOX_SOC_INSIGHTS_CUSTOM_COMMAND = '''
    | infobloxsocinsights type={}, account_name={}, insight_id={}
'''

INFOBLOX_SOC_INSIGHTS_DETAIL_INDEX_SEARCH = '''
    | search `infoblox_index` sourcetype="infoblox_soc_insights_{}" insight_id={}
'''


@Configuration()
class InfoBloxSOCInsightsDetails(GeneratingCommand):
    """Infoblox Tide Lookup custom command."""

    insight_type = Option(name="type", require=True)
    insight_id = Option(name="insight_id", require=True)
    account_name = Option(name="account_name", require=True)

    def validate(self):
        """Validate method."""
        if self.insight_type not in ("events", "assets", "indicators", "comments"):
            logger.info(
                f"message=command_error | Infoblox Error : Given Type parameter '{self.insight_type}' is not valid."
            )
            raise Exception("Given Type parameter is not valid.")

        if not self.account_name:
            logger.info("message=command_error | Infoblox Error : Infoblox Account is required.")
            raise Exception("Infoblox Account is required.")

    def get_search_query(self, is_custom_command=False):
        """Get search method."""
        if is_custom_command:
            logger.info(
                "message=command_info | Infoblox Info : No results found in index using search for '{}' type.".format(
                    self.insight_type
                )
            )
            logger.info("message=command_info | Infoblox Info : Running infobloxsocinsights custom command.")
            return INFOBLOX_SOC_INSIGHTS_CUSTOM_COMMAND.format(self.insight_type, self.account_name, self.insight_id)
        else:
            logger.info("message=command_info | Infoblox Info : Running index search.")
            return INFOBLOX_SOC_INSIGHTS_DETAIL_INDEX_SEARCH.format(self.insight_type, self.insight_id)

    def run_search_query(self, service, kwargs_oneshot, is_custom_command=False):
        """Run a search query and return the results."""
        searchquery_oneshot = self.get_search_query(is_custom_command)
        return results.ResultsReader(
            service.jobs.oneshot(
                searchquery_oneshot, **kwargs_oneshot
            )
        )

    def generate(self):
        """Generate method."""
        try:
            logger.info("message=command_start_execution | Infoblox Info : Started Custom Command Script Execution.")
            start_time = time.time()
            session_key = self.metadata.searchinfo.session_key
            logger.info(
                f"message=command_start_execution | Infoblox Info : Provided params are"
                f" type: '{self.insight_type}', insight_id: '{self.insight_id}',"
                f" and account_name: '{self.account_name}'."
            )
            kwargs_oneshot = {
                "count": 0,
                "earliest_time": str(self._metadata.searchinfo.earliest_time),
                "latest_time": str(self._metadata.searchinfo.latest_time),
            }
            self.validate()

            splunkd_uri = self.metadata.searchinfo.splunkd_uri.split(":")
            service = client.connect(
                host=splunkd_uri[1].strip("/"),
                port=splunkd_uri[2].strip("/"),
                scheme=splunkd_uri[0],
                app=import_declare_test.ta_name,
                token=session_key,
            )

            result = self.run_search_query(service, kwargs_oneshot)

            is_data_present_in_index = False
            count = 0
            logger.info(
                "message=command_info | Infoblox Info : Data Retrived using search for '{}' type.".format(
                    self.insight_type
                )
            )
            for data in result:
                is_data_present_in_index = True
                count += 1
                yield data

            if not is_data_present_in_index:
                result = self.run_search_query(service, kwargs_oneshot, True)
                logger.info(
                    "message=command_info | Infoblox Info : Data Retrived using custom command for '{}' type.".format(
                        self.insight_type
                    )
                )
                for data in result:
                    count += 1
                    yield data

        except Exception:
            logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self.write_error(
                "Insufficient permissions to run custom commands or unexpected error."
                " Please see ta_infoblox_soc_insights_details_custom_command.log file for more information."
            )
            exit(0)
        finally:
            logger.info("message=command_info | Infoblox Info : Total events received: {}.".format(count))
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, time.time() - start_time
                )
            )


dispatch(InfoBloxSOCInsightsDetails, sys.argv, sys.stdin, sys.stdout, __name__)
