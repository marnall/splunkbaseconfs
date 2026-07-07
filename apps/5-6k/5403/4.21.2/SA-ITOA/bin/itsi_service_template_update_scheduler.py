# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input that performs scheduled sync from service templates to services
"""

import sys
import time

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.itoa_common import modular_input_should_run
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from itsi.service_template.service_template_utils import ServiceTemplateUpdateJobProcesser
from ITOA.storage.itoa_storage import ITOAStorage

from SA_ITOA_app_common.solnlib.modular_input import ModularInput


class ITSIServiceTemplateUpdateScheduler(ModularInput):
    """
    Modular Input that performs scheduled sync from service templates to services
    """

    title = 'IT Service Intelligence Service Template Update Scheduler'
    description = 'Performs scheduled sync from service templates to services.'
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_service_template_update_scheduler'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [{
            'name': "log_level",
            'title': "Logging Level",
            'description': "This is the level at which the modular input will log data."
        }]

    @skip_run_during_migration
    def do_run(self, input_config):
        """
        - This is the method called by splunkd when mod input is enabled.
        @param input_config: config passed down by splunkd
        """
        logger = getLogger4ModInput(input_config)
        logger.debug('Checking for pending service template sync job.')

        if not modular_input_should_run(self.session_key, logger):
            return

        self.jobs_processor = ServiceTemplateUpdateJobProcesser(self.session_key)

        kvstore = ITOAStorage()
        if kvstore.wait_for_storage_init(self.session_key):
            self.jobs_processor.run()
        else:
            logger.error('KV Store unavailable for Service Template Update Scheduler. Exiting.')
            sys.exit(1)


if __name__ == "__main__":
    worker = ITSIServiceTemplateUpdateScheduler()
    worker.execute()
    sys.exit(0)
