import import_declare_test
import sys
import time
import traceback
from silent_push_helpers.logger_manager import setup_logging
from silent_push_helpers.rest_helper import RestHelper
from silent_push_helpers.conf_helper import get_credentials
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

logger = setup_logging("ta_silent_push_asnseen_for_domain_custom_command")


@Configuration()
class SilentPushPadnsAsseenfordomainCommand(GeneratingCommand):
    """SilentPushPadnsAsseenfordomainCommand Class."""

    account_name = Option(name="account_name", require=True)
    domain = Option(name="domain", require=True)
    result_format = Option(name="result_format", require=False)
    asnum = Option(name="asnum", require=False)
    sort = Option(name="sort", require=False)
    limit = Option(name="limit", require=False)
    skip = Option(name="skip", require=False)

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
        params = {'result_format': self.result_format}
        if self.asnum:
            params['asnum'] = self.asnum
        if self.limit:
            params['limit'] = self.limit
        if self.skip:
            params['skip'] = self.skip
        if self.sort is not None:
            sort_list = self.sort.split(';')
            params.update({"sort": sort_list})
        data = rest_helper_obj.get_padns_assen_for_domain(self.domain, params)
        error = data.get("response").get("error")
        if error is not None:
            self.logger.error(
                "message=command_error | Error occured while getting padns forward lookup data: {}".format(
                    traceback.format_exc()
                )
            )
            raise Exception(error)
        else:
            for event in data['response']['records']:
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


dispatch(SilentPushPadnsAsseenfordomainCommand, sys.argv, sys.stdin, sys.stdout, __name__)
