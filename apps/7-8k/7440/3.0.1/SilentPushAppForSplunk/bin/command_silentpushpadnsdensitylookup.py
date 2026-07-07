import import_declare_test
import sys
import time
import traceback
from silent_push_helpers.logger_manager import setup_logging
from silent_push_helpers.rest_helper import RestHelper
from silent_push_helpers.conf_helper import get_credentials
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
logger = setup_logging("ta_silent_push_density_lookup_custom_command")


@Configuration()
class SilentPushPadnsDensityLookupCommand(GeneratingCommand):
    """SilentPushPadnsDensityLookupCommand Class."""

    account_name = Option(name="account_name", require=True)
    qtype = Option(name="qtype", require=True)
    scope = Option(name="scope", require=False)
    query = Option(name="query", require=True)

    def generate(self):
        """Generate method."""
        logger.info("message=command_start_execution | Started Custom Command Script Execution.")
        start_time = time.time()
        session_key = self._metadata.searchinfo.session_key
        account_info = get_credentials(self.account_name, session_key)

        silent_push_config = {
            "session_key": session_key
        }
        silent_push_config.update(account_info)

        rest_helper_obj = RestHelper(silent_push_config, logger)
        params = dict()

        if self.scope:
            params.update({'scope': self.scope})

        data = rest_helper_obj.get_padns_density_lookup(self.qtype, self.query, params)
        for event in data.get('response', {}).get('records', []):
            if event.get("error"):
                self.logger.error(
                    "message=command_error | Error occured while getting padns density lookup data: {}".format(
                        traceback.format_exc()
                    )
                )
                raise Exception(event.get("error"))
            else:
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


dispatch(SilentPushPadnsDensityLookupCommand, sys.argv, sys.stdin, sys.stdout, __name__)
