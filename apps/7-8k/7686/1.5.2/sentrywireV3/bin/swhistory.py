import sys
import os
import time
from swstorage import SentryWireStore
from swutils import *
from swconst import *

try:
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
except ImportError as e:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "lib"))
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class SentrywireHistoryCommand(StreamingCommand):
    
    def stream(self, events):
        logger = setup_logging()
        if SENTRYWIRE_DEBUG_MODE:
            logger.warning("Debug mode is enabled! This disables SSL checks!")

        splunk_user = self._metadata.searchinfo.username
        db = SentryWireStore()
        if len(entries := db.get_searches(splunk_user=splunk_user)) < 1:
            msg = f"No search history available for '{splunk_user}'"
            logger.error(msg)
            raise Exception(msg)
        else:
            results = []
            for entry in entries:
                try:
                    search_key = entry[0]
                    search_filter = entry[2]
                    begin_time = entry[3]
                    end_time = entry[4]
                    submitted_time = entry[5]
                    check_status_link = entry[6]
                    get_pcaps_link = entry[7]
                    metadata_link = entry[8]
                    objects_link = entry[9]
                except Exception as e:
                    raise Exception(f"Failed to parse stored history")

                results.append({
                    '_time': submitted_time,
                    'searchname': search_key,
                    'search_filter': search_filter,
                    'checkstatus': check_status_link,
                    'getpcaps': get_pcaps_link,
                    'metadata': metadata_link,
                    'objects': objects_link
                })
            return results


try:
    dispatch(SentrywireHistoryCommand, sys.argv, sys.stdin, sys.stdout, __name__)
except Exception as e:
    print(str(e))