# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from ITOA.splunk_search_chunk_protocol import SearchChunkProtocol
from itsi.itsi_utils import ITOAInterfaceUtils
from ITOA.setup_logging import logger

ITSI_HEALTH_CHECK_DB_URI = '/app/itsi/itsi_healthcheck'
WARNING_MESSAGE = ('Duplicate entity aliases found. This may cause incorrect statistical '
                   'aggregation results for KPI base searches. [[{}|Show duplicates.]]').format(ITSI_HEALTH_CHECK_DB_URI)


class CheckForDupAliasCommand(SearchChunkProtocol):
    """
    A wrapper class to utilize search chunk protocol
    """

    def __init__(self):
        """
        Initializes the get discovery status custom search command to be compatible with the
        splunk search chunk protocol
        """
        hand_shake_output_data = {
            'type': 'reporting'
        }
        super(CheckForDupAliasCommand, self).__init__(output_meta_data=hand_shake_output_data, logger=logger)
        self.read_results = []

    def run(self, metadata, reader, chunk):
        """
        Read the chunk data, to then be processed the results
        @return:
        """
        self.read_results.extend([r for r in reader])
        self.write_chunk({'finished': False}, '')

    def post_processing(self):
        """
        Check the search results and post the warning message when there is duplicates
        """
        settings = {
            'sessionKey': self.session_key
        }

        results = self.read_results
        if len(results):
            ITOAInterfaceUtils.create_message(settings['sessionKey'], WARNING_MESSAGE)

        else:
            logger.debug('No duplicated aliases found for all ITSI entities.')

        self.write_chunk({'finished': True}, '')


if __name__ == "__main__":
    try:
        status = CheckForDupAliasCommand()
        status.execute()
    except Exception as e:
        logger.exception(e)
