# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import csv
import json

from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.rest as rest

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from ITOA.splunk_search_chunk_protocol import SearchChunkProtocol
from itsi.itsi_utils import ITOAInterfaceUtils
from ITOA.setup_logging import logger


class CheckForKvstoreSize(SearchChunkProtocol):
    """
    A wrapper class to utilize search chunk protocol
    """

    def __init__(self):
        """
        Initialize the search command

        """
        hand_shake_output_data = {
            'type': 'reporting'
        }
        super(CheckForKvstoreSize, self).__init__(output_meta_data=hand_shake_output_data, logger=logger)
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
        Check the search results and post the warning message when KVStore size is larger than the limits
        """
        settings = {
            'sessionKey': self.session_key
        }
        collection_size = 0
        limit_from_conf = 1

        try:
            # Obtain the current itsi_services collection size
            results = self.read_results
            if len(results):
                for row in results:
                    if row.get('Collection') == 'itsi_services':
                        collection_size = float(row.get('Collection Size (MB)'))
                        limit_from_conf = float(row.get('KVStore Limit Max Size (MB)'))

        except Exception:
            logger.exception('Unable to check the kvstore size')

        if collection_size > limit_from_conf:
            ERROR_MESSAGE = (
                'The itsi_services collection size is {0} MB which is larger than the KV store '
                'results limit. Increase the max_size_per_result_mb and max_size_per_batch_result_mb '
                'in SA_ITOA/local/limits.conf to more than {0} MB.'
            ).format(round(collection_size, 2))
            ITOAInterfaceUtils.create_message(settings['sessionKey'], ERROR_MESSAGE, severity='error')
        elif collection_size > limit_from_conf * 0.9:
            WARNING_MESSAGE = (
                'The itsi_services collection size is {0} MB which is approaching the KV store results limit of {1} '
                'MB. Increase the max_size_per_result_mb and max_size_per_batch_result_mb in SA_ITOA/local/limits.conf '
                'to more than {1} MB to avoid potential future data loss.'
            ).format(round(collection_size, 2), limit_from_conf)
            ITOAInterfaceUtils.create_message(settings['sessionKey'], WARNING_MESSAGE, severity='warn')

        self.write_chunk({'finished': True}, '')


if __name__ == "__main__":
    try:
        status = CheckForKvstoreSize()
        status.execute()
    except Exception as e:
        logger.exception(e)
