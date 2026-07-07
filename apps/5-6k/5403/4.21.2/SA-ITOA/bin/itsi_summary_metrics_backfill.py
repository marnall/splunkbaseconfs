# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

'''
Modular Input that dispatches search jobs for moving data from
itsi_summary to itsi_summary_metrics index.
'''

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path

from ITOA.setup_logging import getLogger4ModInput
from itsi.metrics_backfill import MetricsBackfillQueue
from ITOA.itoa_common import modular_input_should_run
from SA_ITOA_app_common.solnlib.modular_input import ModularInput


class ItsiMetricsBackfillModularInput(ModularInput):
    '''
    Mod input that moves data from event summary index to metric index
    '''

    title = 'IT Service Intelligence Metrics Backfill Process Queue'
    description = 'Supervises long-running backfill jobs that populate metric index from summary index.'
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_metrics_backfill_queue'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [{
            'name': 'log_level',
            'title': 'Logging Level',
            'description': 'This is the level at which the modular input will log data.'
        }, {
            'name': 'metrics_backfill_throttle',
            'title': 'ITSI Summary Metrics Backfill Throttle',
            'description': ('The interval, in seconds, that specifies how long the backfill modular input should '
                            'pause in between executing the concurrent backfill searches.')
        }, {
            'name': 'metrics_backfill_length',
            'title': 'ITSI Summary Metrics Backfill Length',
            'description': ('The length of time, in days, that specifies how far back the backfill operation '
                            'should run over. The more days run for the backfill, the longer the operation will '
                            'take.')
        }, {
            'name': 'metrics_backfill_concurrent_searches',
            'title': 'ITSI Summary Metrics Backfill Concurrent Searches',
            'description': ('The number of concurrent searches the backfill modular input should run. More '
                            'concurrent searches will allow the backfill to complete faster, but will likely lead'
                            ' to a higher impact on the indexers.')
        }]

    def do_run(self, input_config):
        """
        - This is the method called by splunkd when mod input is enabled.
        @type input_config: object
        @param input_config: config passed down by splunkd
            input_config is a dictionary key'ed by the name of the modular
            input, its value is the modular input configuration.
        """
        logger = getLogger4ModInput(input_config)

        # input_config is a dictionary: Key = name of the modular input, Value = a dict of the mod_input configuration.
        # To get the values, convert to a list and just return the first entry, which will be the original dict value
        config_settings = list(input_config.values())[0]

        if modular_input_should_run(self.session_key, logger):
            MetricsBackfillQueue(self.session_key, logger).execute_backfill_queue(config_settings=config_settings)


if __name__ == '__main__':
    worker = ItsiMetricsBackfillModularInput()
    worker.execute()
    sys.exit(0)
