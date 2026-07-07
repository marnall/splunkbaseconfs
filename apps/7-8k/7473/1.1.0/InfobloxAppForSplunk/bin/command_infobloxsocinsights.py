import import_declare_test
import sys
import time
import traceback
import json
import requests
from datetime import datetime
from infoblox_helpers.kvstore import CollectionManager
from infoblox_helpers.logger_manager import setup_logging
from infoblox_helpers.conf_helper import get_credentials
from infoblox_helpers.rest_helper import RestHelper
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option


logger = setup_logging("ta_infoblox_soc_insights_custom_command")


@Configuration()
class InfoBloxSOCInsights(GeneratingCommand):
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

    def generate(self):
        """Generate method."""
        try:
            logger.info("message=command_start_execution | Infoblox Info : Started Custom Command Script Execution.")
            start_time = time.time()
            session_key = self._metadata.searchinfo.session_key
            logger.info(
                f'message=command_start_execution | Infoblox Info : Provided params are'
                f' type: {self.insight_type}, value: {self.insight_id}, and account_name: {self.account_name}.'
            )
            self.validate()
            account_info = get_credentials(self.account_name, session_key)
            infoblox_config = {
                "session_key": session_key
            }
            infoblox_config.update(account_info)

            rest_helper_obj = RestHelper(infoblox_config, logger)

            data = rest_helper_obj.get_soc_insight_details(self.insight_type, self.insight_id)

            logger.info(
                "message=command_info | Infoblox Info : Json Data Retrived for {} type.".format(
                    self.insight_type
                )
            )

            for event in data.get(self.insight_type, []):
                yield {
                    "_raw": json.dumps(event, ensure_ascii=False),
                    "_time": time.time()
                }
        except Exception:
            logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self.write_error(
                "Insufficient permissions to run custom commands or unexpected error."
                " Please see ta_infoblox_soc_insights_custom_command.log file for more information."
            )
            exit(0)
        finally:
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, time.time() - start_time
                )
            )


dispatch(InfoBloxSOCInsights, sys.argv, sys.stdin, sys.stdout, __name__)
