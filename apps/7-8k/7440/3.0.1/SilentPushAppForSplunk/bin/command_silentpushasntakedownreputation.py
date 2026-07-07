import import_declare_test
import sys
import time
import json
from silent_push_helpers.logger_manager import setup_logging
from silent_push_helpers.rest_helper import RestHelper
from silent_push_helpers.conf_helper import get_credentials
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option


logger = setup_logging("ta_silent_push_asn_takedown_reputation_custom_command")


@Configuration()
class SilentPushAsnTakeDownReputation(GeneratingCommand):
    """Silent Push asn takedown reputation custom command."""

    explain = Option(name="explain", require=False)
    asn = Option(name="asn", require=True)
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

        data = rest_helper_obj.get_asn_takedown_reputation(self.asn, params)

        logger.info("message=command_info | Silent Push Info : Json Data Retrived.")
        resp = data.get("response", {})
        for key, value in resp.items():
            yield {
                "_raw": json.dumps(value),
                "_time": time.time()
            }

        logger.info(
            'message=command_end_execution | End of the "{}" command execution.'
            " Total time taken: elapsed_seconds={:.3f}".format(
                self.name, time.time() - start_time
            )
        )


dispatch(SilentPushAsnTakeDownReputation, sys.argv, sys.stdin, sys.stdout, __name__)
