import import_declare_test
import sys
import time
import traceback
import json
from infoblox_helpers.logger_manager import setup_logging
from infoblox_helpers.conf_helper import get_credentials
from infoblox_helpers.rest_helper import RestHelper
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option


logger = setup_logging("ta_infoblox_named_list_custom_command")


@Configuration()
class InfoBloxNamedList(GeneratingCommand):
    """Infoblox Named List custom command."""

    account_name = Option(name="account_name", require=True)

    def generate(self):
        """Generate method."""
        try:
            logger.info("message=command_start_execution | Infoblox Info : Started Custom Command Script Execution.")
            start_time = time.time()
            session_key = self._metadata.searchinfo.session_key
            logger.info(
                f'message=command_start_execution | Infoblox Info : Provided params are'
                f' account_name: {self.account_name}.'
            )
            account_info = get_credentials(self.account_name, session_key)

            infoblox_config = {
                "session_key": session_key
            }
            infoblox_config.update(account_info)

            rest_helper_obj = RestHelper(infoblox_config, logger)
            params = {
                "_fields": "name,id"
            }

            data = rest_helper_obj.get_named_lists(params)
            logger.info("message=command_info | Infoblox Info : Json Data Retrived.")

            for event in data.get("results", []):
                if not event.get("name", "").startswith("Threat Insight"):
                    yield {
                        "_raw": event
                    }
        except Exception:
            logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self.write_error(
                "Insufficient permissions to run custom commands or unexpected error."
                " Please see ta_infoblox_named_list_custom_command.log file for more information."
            )
            exit(0)
        finally:
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, time.time() - start_time
                )
            )


dispatch(InfoBloxNamedList, sys.argv, sys.stdin, sys.stdout, __name__)
