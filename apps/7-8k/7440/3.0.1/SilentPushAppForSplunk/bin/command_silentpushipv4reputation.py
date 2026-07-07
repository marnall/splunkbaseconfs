import import_declare_test
import sys
import time
from silent_push_helpers.logger_manager import setup_logging
from silent_push_helpers.rest_helper import RestHelper
from silent_push_helpers.conf_helper import get_credentials
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option


logger = setup_logging("ta_silent_push_ipv4_reputation_custom_command")


@Configuration()
class SilentPushIPv4Reputation(GeneratingCommand):
    """Silent Push ipv4 reputation custom command."""

    explain = Option(name="explain", require=False)
    ipv4 = Option(name="ipv4", require=True)
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

        silent_push_config.update(account_info)

        rest_helper_obj = RestHelper(silent_push_config, logger)
        if self.explain:
            params = {
                'explain': self.explain
            }
        else:
            params = None

        data = rest_helper_obj.get_ipv4_reputation(self.ipv4, params)

        logger.info("message=command_info | Silent Push Info : Json Data Retrived.")
        for event in data.get("response", {}).get("ip_reputation", ""):
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


dispatch(SilentPushIPv4Reputation, sys.argv, sys.stdin, sys.stdout, __name__)
