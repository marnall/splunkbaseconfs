# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.itoa_common import modular_input_should_run
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from itsi.searches.kpi_summary_cache_retention_policy import KPISummaryCacheRetentionPolicy
from ITOA.storage.itoa_storage import ITOAStorage

from SA_ITOA_app_common.solnlib.modular_input import ModularInput


class ItsiAgeKpiSummaryCacheModularInput(ModularInput):
    """
    Modular input which cleans up aged KPI summary entries from kvstore
    collection (itsi_kpi_summary_cache), used to cache KPI Summary results.
    """
    title = 'IT Service Intelligence KPI Summary Cache Cleaner'
    description = 'Deletes the aged KPI Summary entries from the KPI Alert Value Cache.'
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_age_kpi_alert_value_cache'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [
            {
                'name': 'log_level',
                'title': 'Logging Level',
                'description': 'This is the level at which the modular input will log data.'
            },
            {
                'name': 'retentionTimeInSec',
                'title': 'Retention Time',
                'description': 'Aging/retention time in seconds for entries present in KPIs Summary Cache.'
            }
        ]

    @skip_run_during_migration
    def do_run(self, input_config):
        """
        This is the method called by splunkd when mod input is enabled.
        @param input_config: input config for mod input
        """

        logger = getLogger4ModInput(input_config, 'itsi.objects.searches')
        if not modular_input_should_run(self.session_key, logger=logger):
            logger.info("Will not run modular input on this node")
            return

        # default retention time to 900 seconds if not provided
        retention_time = input_config.get('retentionTimeInSec', 900)
        retention_policy = KPISummaryCacheRetentionPolicy(self.session_key, retention_time, logger=logger)

        kvstore = ITOAStorage()
        if kvstore.wait_for_storage_init(self.session_key):
            retention_policy.run()
        else:
            logger.error('KV Store unavailable for cleaning up KPI Summary Cache. Exiting.')
            sys.exit(1)


if __name__ == "__main__":
    worker = ItsiAgeKpiSummaryCacheModularInput()
    worker.execute()
    sys.exit(0)
