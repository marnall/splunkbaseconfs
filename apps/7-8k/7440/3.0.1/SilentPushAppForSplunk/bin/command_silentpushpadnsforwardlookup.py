import import_declare_test
import sys
import time
import traceback
from silent_push_helpers.logger_manager import setup_logging
from silent_push_helpers.rest_helper import RestHelper
from silent_push_helpers.conf_helper import get_credentials
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
logger = setup_logging("ta_silent_push_forward_lookup_custom_command")


@Configuration()
class SilentPushPadnsForwardLookupCommand(GeneratingCommand):
    """SilentPushPadnsForwardLookupCommand Class."""

    account_name = Option(name="account_name", require=True)
    qtype = Option(name="qtype", require=True)
    qname = Option(name="qname", require=True)
    netmask = Option(name="netmask", require=False)
    subdomains = Option(name="subdomains", require=False)
    with_metadata = Option(name="with_metadata", require=False)
    regex = Option(name="regex", require=False)
    match = Option(name="match", require=False)
    first_seen_before = Option(name="first_seen_before", require=False)
    first_seen_after = Option(name="first_seen_after", require=False)
    last_seen_before = Option(name="last_seen_before", require=False)
    last_seen_after = Option(name="last_seen_after", require=False)
    as_of = Option(name="as_of", require=False)
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
        params = {
            'netmask': self.netmask,
            'subdomains': self.subdomains,
            'with_metadata': self.with_metadata,
            'regex': self.regex,
            'match': self.match,
            'first_seen_before': self.first_seen_before,
            'first_seen_after': self.first_seen_after,
            'last_seen_before': self.last_seen_before,
            'last_seen_after': self.last_seen_after,
            'sort': self.sort,
            'as_of': self.as_of,
            'limit': self.limit,
            'skip': self.skip,
        }
        if self.sort is not None:
            sort_list = self.sort.split(';')
            params.update({"sort": sort_list})

        data = rest_helper_obj.get_padns_forward_lookup(self.qtype, self.qname, params)

        error = data.get("response").get("error")

        if error is not None:
            self.logger.error(
                "message=command_error | Error occured while getting padns forward lookup data: {}".format(
                    traceback.format_exc()
                )
            )
            raise Exception(error)
        else:
            metadata = data.get("response", {}).get("metadata", {})
            job_status = data.get("response", {}).get("job_status", {})
            if job_status:
                yield {
                    "_raw": job_status,
                    "_time": time.time()
                }
                return
            for event in data.get('response', {}).get('records', []):
                if self.with_metadata == "1":
                    event.update({"metadata": metadata})
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


dispatch(SilentPushPadnsForwardLookupCommand, sys.argv, sys.stdin, sys.stdout, __name__)
