import import_declare_test
import sys
import time
from silent_push_helpers.logger_manager import setup_logging
from silent_push_helpers.rest_helper import RestHelper
from silent_push_helpers.conf_helper import get_credentials
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option


logger = setup_logging("ta_silent_push_web_scan_data_custom_command")


@Configuration()
class SilentPushWebScanData(GeneratingCommand):
    """Silent Push web scan custom command."""

    query = Option(name="query", require=True)
    sort = Option(name="sort", require=False)
    limit = Option(name="limit", require=False, default="100")
    page = Option(name="page", require=False, default="1")
    account_name = Option(name="account_name", require=True)

    def generate(self):
        """Generate method."""
        logger.info("message=command_start_execution | Silent Push Info : Started Custom Command Script Execution.")
        start_time = time.time()
        session_key = self._metadata.searchinfo.session_key
        account_info = get_credentials(self.account_name, session_key)

        silent_push_config = {
            "session_key": session_key
        }

        params = dict()
        payload = dict()

        if self.sort:
            payload['sort'] = self.sort.split(',')

        payload["query"] = self.query
        params["skip"] = str((int(self.page) - 1) * int(self.limit))
        params["limit"] = self.limit
        params["with_metadata"] = '1'

        silent_push_config.update(account_info)

        rest_helper_obj = RestHelper(silent_push_config, logger)

        data = rest_helper_obj.get_web_scan_data(params, payload)

        logger.info("message=command_info | Silent Push Info : Json Data Retrived.")
        for event in data:
            yield {
                "_raw": event,
                "_time": time.time()
            }

        logger.info(
            'message=command_end_execution | End of the "{}" command execution.'
            " Total time taken: elapsed_seconds={:.3f}".format(
                self.name, time.time() - start_time
            )
        )


dispatch(SilentPushWebScanData, sys.argv, sys.stdin, sys.stdout, __name__)
