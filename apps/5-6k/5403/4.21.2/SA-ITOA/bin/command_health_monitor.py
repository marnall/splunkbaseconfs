# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import csv
import traceback

# Core Splunk Imports
import splunk.rest
import splunk.Intersplunk
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.setup_logging import logger
from ITOA.itoa_common import get_log_message_for_exception
from ITOA.splunk_search_chunk_protocol import SearchChunkProtocol
from itsi.searches.compute_health_score import HealthMonitor


def is_debug_flag_is_set(args):
    '''
    Parse search arguments and return if debug flag is set
    :return: flag if debug is set or not
    :rtype: boolean
    '''
    i = 1
    debug = False
    while i < len(args):
        arg = args[i]
        if arg.find('debug=') != -1:
            debug = arg[arg.find('debug=') + 6:]
        else:
            splunk.Intersplunk.parseError("Invalid argument '%s'." % arg)
        i += 1
    return debug


class HealthMonitorCommand(SearchChunkProtocol):
    """
    A Wrapper to utilize all the SearchChunkProtocol for the health monitor command
    """
    def __init__(self):
        """
        Initializes the service health score monitor custom search command to be compatible with the
        splunk search chunk protocol
        """
        hand_shake_output_data = {
            'type': 'reporting'
        }
        super(HealthMonitorCommand, self).__init__(output_meta_data=hand_shake_output_data, logger=logger)
        # if service_id argument is passed to the command. then, it means
        # it is a backfill request for service health score calculation.
        self.service_id = self.args.get('service_id')
        self.read_results = []

    def run(self, metadata, reader, chunk):
        """
        Read the chunk data, to then be processed for the health score calculation
        @return:
        """
        self.read_results.extend([r for r in reader])
        self.write_chunk({'finished': False}, '')

    def post_processing(self):
        """
        Performs the healthscore calculation on the read in results and writes them to
        an output buffer
        @return: None
        """
        settings = {
            'sessionKey': self.session_key,
            'service_id': self.service_id
        }
        hm = HealthMonitor(self.read_results, settings, is_debug)
        results = hm.execute()
        rval_chunk = ''
        if results:
            output_buf = self.get_string_buffer()
            fieldnames = hm.get_output_fields()
            writer = csv.DictWriter(output_buf, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(r)
            # overwrite rval_chunk to something more meaningful since we have results.
            rval_chunk = output_buf.getvalue()

        # finally, return a chunk.
        self.write_chunk({'finished': True}, rval_chunk)


if __name__ == "__main__":
    hmc = None
    is_debug = is_debug_flag_is_set(sys.argv)
    try:
        hmc = HealthMonitorCommand()
        hmc.execute()
    except Exception as e:
        if "Splunkd daemon is not responding: " in str(e):
            logger.warning('Connection issue. "%s". If this message occurs only once, KV Store may still be initializing.', e)
        else:
            logger.exception(e)
            logger.exception(traceback.format_exc())
        if hmc is not None:
            hmc.exit_with_error({'finished': True}, [get_log_message_for_exception(e)])
        else:
            raise
