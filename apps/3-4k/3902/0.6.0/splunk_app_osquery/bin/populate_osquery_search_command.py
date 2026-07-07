"""
This search command populates the list of queries with a default set.
"""

import sys
import logging

import splunk.rest
from splunk.util import normalizeBoolean

from search_command import SearchCommand
from kvstore_deserialize import KVStoreDeserializer

class PopulateOSQueryData(SearchCommand):
    """
    This the search command that serialize the JSON files back into the KV store collection.
    """

    def __init__(self, force=True):

         # Initialize the class
        SearchCommand.__init__(self, run_in_preview=True,
                               logger_name='populate_osquery_search_command',
                               log_level=logging.DEBUG)

        self.force = normalizeBoolean(force)

    def handle_results(self, results, session_key, in_preview):

        try:
            imported_count = self.make_data(session_key, self.force)

            self.logger.info("Command ran successfully. rows_imported=%i", imported_count)

            self.output_results([
                {
                    'status' : 'Command ran successfully',
                    'rows_imported' : imported_count
                }])
        except Exception as exception:
            self.logger.exception("Unable to populate the queries")
            self.output_results([{'status' : 'Command failed: ' + str(exception)}])

    def make_data(self, session_key, force=False):
        """
        Initiate the process to make the data.
        """
        self.logger.info("Collection is empty? %r", KVStoreDeserializer.is_collection_empty(session_key, "nobody", "splunk_app_osquery", "saved_osqueries", logger=self.logger))
        if force or KVStoreDeserializer.is_collection_empty(session_key, "nobody", "splunk_app_osquery", "saved_osqueries", logger=self.logger):
            return KVStoreDeserializer.load_data_for_app(session_key, "splunk_app_osquery", logger=self.logger)

# If this is run from the command-line, then execute as a search-command.
if __name__ == '__main__':
    try:
        PopulateOSQueryData.execute()
        sys.exit(0)
    except Exception as e:
        print e
