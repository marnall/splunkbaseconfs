import datetime
import os
import re
import sys

# Add the "lib" directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

from util import setup_logging

from constants import KV_AT_TIME_POLICIES_COLLECTION

# Set up logger
logger = setup_logging.get_logger()

DEFAULT_RETENTION_HOURS = 1


@Configuration()
class CleanUpKVStoreCommand(GeneratingCommand):
    retention_hours = Option(require=False, validate=validators.Integer(0))

    @staticmethod
    def extract_epoch_from_sid(sid: str) -> int:
        """
        Extract the epoch timestamp from a given Splunk Search ID (SID).
        But heads up, it currently only works with Normal Search Job SIDs and Scheduled Search Job SIDs.

        :param sid: The Splunk Search ID (SID)
        :return: The extracted epoch timestamp as an integer
        """
        # Check if the SID contains an underscore, indicating a more complex format
        if '_' in sid:
            match = re.search(r'_at_(\d+)_', sid)
            if match:
                return int(match.group(1))

        # If the SID is a simple format, extract the epoch timestamp directly
        match = re.search(r'^(\d+)', sid)
        if match:
            return int(match.group(1))

        raise ValueError(f"Cannot extract epoch timestamp from SID: {sid}")

    def generate(self):
        try:
            # Set default retention_hours if not provided
            retention_hours = DEFAULT_RETENTION_HOURS if self.retention_hours is None else self.retention_hours

            logger.info(f"Configured data retention hours: {retention_hours} hours")

            # Calculate the retention time in seconds
            retention_seconds = retention_hours * 3600

            # Iterate over KV store records and delete those older than the retention time
            now = datetime.datetime.utcnow()
            collection = self.service.kvstore[KV_AT_TIME_POLICIES_COLLECTION]
            for record in collection.data.query():
                sid = record["_key"]
                sid_datetime = datetime.datetime.utcfromtimestamp(self.extract_epoch_from_sid(sid))
                if (now - sid_datetime).total_seconds() > retention_seconds:
                    collection.data.delete_by_id(sid)

            yield {'result': 'Clean up successful'}
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            yield {'result': 'Clean up unsuccessful'}


dispatch(CleanUpKVStoreCommand, sys.argv, sys.stdin, sys.stdout, __name__)
