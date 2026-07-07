import ta_intsights_declare  # noqa: F401
import os
import sys
import time
import json
import traceback
from datetime import datetime, timedelta

from api_client import APIClient
from intsights_utils import generate_query_list_for_lookups
from command_utils import IOCsManager
from log_manager import setup_logging, generate_log_file_name
from splunklib.searchcommands import (
    Configuration,
    GeneratingCommand,
    dispatch,
)
from errors import CustomException

logger_name = os.path.splitext(os.path.basename(__file__))[0]
logger = setup_logging(logger_name)
KEY_WHITELIST_CHECKPOINTER = "whitelistCheckPointer"
CHECKPOINT_NAME = "intsights_whitelist_checkpointer"
LAST_RUN_TIME = "lastRunTime"
NEXT_OFFSET = "nextOffset"


@Configuration()
class IntSightsDeleteWhitelist(GeneratingCommand):
    """Intsights delete whitelist custom command."""

    def generate(self):
        """Generate events."""
        if False:
            yield
        starttime = time.time()
        logger.info('Starting the "{}" command execution.'.format(self.name))
        logger.info("SID: {}".format(self.metadata.searchinfo.sid))

        try:
            linux_utc_time = datetime.utcnow() - timedelta(hours=4)
            self.session_key = self.search_results_info.auth_token
            api_client = APIClient(self.session_key, logger)
            ioc_manager = IOCsManager(self.service, logger)

            # fetch the lastran whitelist lookup time
            logger.info("Fetching {} checkpoint details".format(CHECKPOINT_NAME))
            wl_checkpoint = ioc_manager.get_intsights_whitelist_checkpoint(
                KEY_WHITELIST_CHECKPOINTER
            )
            logger.info(
                "Fetched {} checkpoint details successfully".format(CHECKPOINT_NAME)
            )
            created_date = None
            next_offset = None
            offset = True
            if wl_checkpoint:
                if wl_checkpoint.get(LAST_RUN_TIME):
                    created_date = datetime.utcfromtimestamp(
                        wl_checkpoint.get(LAST_RUN_TIME)
                    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                next_offset = wl_checkpoint.get(NEXT_OFFSET)
            logger.info(
                "Getting the whitelisted IOCs from {} time and {} offset".format(
                    created_date if created_date else 0,
                    next_offset if next_offset else 0
                )
            )

            iocs_list = []
            while(offset):  # noqa: E275
                res = api_client.get_deleted_whitelist(created_date, next_offset)
                if res.status_code in (200, 201):
                    res = (json.loads(res.content))
                    response_content = res.get("content")
                    for response in response_content:
                        iocs_list.append(response.get('value'))

                    logger.info(
                        "Received {} whitelisted IOCs to delete".format(
                            len(response_content)
                        )
                    )
                    logger.debug(
                        "Received this IOCs to delete: {}".format(iocs_list)
                    )

                    # Getting the list of queries to make the IOCs delete call from lookups
                    query_list = generate_query_list_for_lookups(iocs_list)
                    logger.info("Deleting whitelisted iocs from lookup tables")
                    for query in query_list:
                        ioc_manager.delete_from_lookups(query)

                    if res.get('nextOffset'):
                        next_offset = res.get('nextOffset')
                        whitelist_checkpoint = [
                            {
                                NEXT_OFFSET: res.get('nextOffset'),
                                "_key": KEY_WHITELIST_CHECKPOINTER,
                            }
                        ]
                        if created_date:
                            whitelist_checkpoint[0][LAST_RUN_TIME] = wl_checkpoint.get(LAST_RUN_TIME)
                        ioc_manager.update_whitelist_checkpoint(
                            whitelist_checkpoint
                        )
                        logger.debug(
                            "IOCs are deleted successfully and updating the offset to {} time".format(
                                next_offset
                            )
                        )
                    else:
                        offset = False
                        ioc_manager.update_whitelist_checkpoint(
                            [
                                {
                                    LAST_RUN_TIME: (
                                        linux_utc_time - datetime(1970, 1, 1)
                                    ).total_seconds(),
                                    "_key": KEY_WHITELIST_CHECKPOINTER,
                                }
                            ]
                        )
            logger.info(
                "IOCs are deleted successfully and updating the checkpoint to {}({}) time".format(
                    linux_utc_time,
                    (linux_utc_time - datetime(1970, 1, 1)).total_seconds(),
                )
            )
        except CustomException as ex:
            logger.error(ex.reason)

            # Display an error message on Splunk UI, below the search panel.
            self.write_error(ex.message)
        except Exception:
            logger.error(
                'Error occured while executing "{}" command -- {}'.format(
                    self.name, traceback.format_exc()
                )
            )
            self.write_error(
                (
                    'Internal error while executing "{cmd_name}" custom command.'
                    " Please check {log_file_name}.log file."
                ).format(
                    cmd_name=self.name,
                    log_file_name=generate_log_file_name(logger_name),
                )
            )

        logger.info("Time taken - {} seconds.".format(time.time() - starttime))
        logger.info('Completed the execution of "{}" command.'.format(self.name))


if __name__ == "__main__":
    dispatch(IntSightsDeleteWhitelist, sys.argv, sys.stdin, sys.stdout, __name__)
