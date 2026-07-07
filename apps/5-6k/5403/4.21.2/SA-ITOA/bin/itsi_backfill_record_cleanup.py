# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import json
import sys

import splunk.rest as rest
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path

from SA_ITOA_app_common.solnlib.modular_input import ModularInput

from ITOA.itoa_common import modular_input_should_run
from ITOA.setup_logging import getLogger4ModInput

BACKFILL_RECORD_URI = '/servicesNS/nobody/SA-ITOA/storage/collections/data/itsi_backfill'


class BackfillRecordCleanup(ModularInput):
    """
    Just a basic modular input responsible for configuring ITSI.
    Here are just one of the many amazing things it does
        - Import entities from the conf file system into the statestore

    """
    title = "IT Service Intelligence Backfill Record CleanUp"
    description = "Configures IT Service Intelligence"
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_backfill_record_cleanup'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def __init__(self):
        # Since logger is used before do_run is called, initialize logger first:
        super(BackfillRecordCleanup, self).__init__()

    def extra_arguments(self):
        return [
            {
                'name': "log_level",
                'title': "Logging Level",
                'description': "This is the level at which the modular input will log data."
            },
        ]

    def do_run(self, input_config):

        logger = getLogger4ModInput(input_config)

        if not modular_input_should_run(self.session_key, logger=logger):
            logger.info("Will not run modular input on this node.")
            return

        num_cancelled_record = 0
        get_args = {}
        get_args['query'] = json.dumps({'status': 'cancelled'})
        try:
            # Try to get the cancelled record first
            response, content = rest.simpleRequest(BACKFILL_RECORD_URI,
                                                   method='GET',
                                                   sessionKey=self.session_key,
                                                   getargs=get_args)
            if response.status in (200, 201):
                num_cancelled_record = len(json.loads(content))

            logger.debug('{} cancelled records found from the backfill collection.'.format(num_cancelled_record))
            if num_cancelled_record:
                response, content = rest.simpleRequest(BACKFILL_RECORD_URI,
                                                       method='DELETE',
                                                       sessionKey=self.session_key,
                                                       getargs=get_args)
                if response.status in (200, 201):
                    logger.debug('Successfully removed all cancelled backfill records.')
        except Exception as e:
            logger.debug('Failed to cleanup backfill record. Message: {}'.format(e))


if __name__ == "__main__":
    worker = BackfillRecordCleanup()
    worker.execute()
    sys.exit(0)
