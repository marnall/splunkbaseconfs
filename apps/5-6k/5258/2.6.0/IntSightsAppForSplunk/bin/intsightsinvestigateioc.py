import ta_intsights_declare     # noqa: F401
import os
import sys
import time
import json
import traceback

from api_client import APIClient
from log_manager import setup_logging, generate_log_file_name
from errors import CustomException
from splunklib.searchcommands import (
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
)

logger_name = os.path.splitext(os.path.basename(__file__))[0]
logger = setup_logging(logger_name)


@Configuration()
class IntSightsInvestigateIOCCommand(GeneratingCommand):
    """
    Intsights investigate IOC value custom command.

    :param: ioc_value: Value of IOC for which investigation details will be fetched
        from IntSights Platform and ingested in Splunk.
    """

    ioc_value = Option(name="ioc_value", require=True)

    def format_as_splunk_event(self, res):
        """Format response as Splunk Event."""
        event = {
            '_raw': json.dumps(res, ensure_ascii=False),
            '_time': time.time(),
        }

        return event

    def generate(self):
        """Generate events."""
        if False:
            yield

        self.starttime = time.time()
        logger.info('Starting the "{}" command execution.'.format(self.name))
        logger.info('SID: {}'.format(self.metadata.searchinfo.sid))

        try:
            self.session_key = self.search_results_info.auth_token
            self.api_client = APIClient(self.session_key, logger)

            logger.info('Fetching an investigation for IOC value - "{}".'.format(self.ioc_value))
            res = self.api_client.get_ioc_investigation(self.ioc_value)
            yield self.format_as_splunk_event(res['content'])

        except CustomException as ex:
            logger.error(ex.reason)

            # Display an error message on Splunk UI, below the search panel.
            self.write_error(ex.message)

        except Exception:
            logger.error('Error occured while executing "{}" command -- {}'.format(self.name, traceback.format_exc()))
            self.write_error((
                'Internal error occured while executing "{}" custom command.'
                ' Please check "{}" file.'
            ).format(self.name, generate_log_file_name(logger_name)))

        logger.info('Time taken - {} seconds.'.format(time.time() - self.starttime))
        logger.info('Completed the execution of "{}" command.'.format(self.name))


if __name__ == "__main__":
    dispatch(IntSightsInvestigateIOCCommand, sys.argv, sys.stdin, sys.stdout, __name__)
