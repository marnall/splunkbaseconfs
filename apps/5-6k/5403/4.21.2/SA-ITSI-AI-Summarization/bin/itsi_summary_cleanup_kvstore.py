import os
import sys

# Add the "lib" directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunklib.searchcommands import (
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
    validators,
)
from util import setup_logging
from work_queue import WorkQueue

# Set up logger
logger = setup_logging.get_logger()

DEFAULT_RETENTION_HOURS = 1


@Configuration()
class CleanUpKVStoreCommand(GeneratingCommand):
    retention_hours = Option(require=False) #validate=validators.Integer(0))

    def generate(self):
        try:
            # Set default retention_hours if not provided
            retention_hours = (
                DEFAULT_RETENTION_HOURS
                if self.retention_hours is None
                else self.retention_hours
            )
            logger.debug(f"Configured data retention hours: {retention_hours} hours")
            logger.debug("Starting KV Store cleanup process")
            work_queue = WorkQueue(self.service)
            purged_count = work_queue.purge_stale_records(retention_hours)
            logger.debug(
                f"KV Store cleanup process completed. Purged {purged_count} records older than {retention_hours} hours"
            )
            yield {"result": "Clean up successful", "purged_count": purged_count}
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            yield {"result": "Clean up unsuccessful"}


dispatch(CleanUpKVStoreCommand, sys.argv, sys.stdin, sys.stdout, __name__)
