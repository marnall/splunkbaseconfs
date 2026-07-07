# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input that runs on schedule to execute content pack authorship job.
"""

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path  # noqa

from SA_ITOA_app_common.solnlib.modular_input import ModularInput

from ITOA.itoa_common import modular_input_should_run, is_feature_enabled
from ITOA.mod_input_utils import skip_run_during_migration
from ITOA.setup_logging import getLogger4ModInput
from itsi.content_pack_authorship.authorship_operation import AuthorshipOperation


class ItsiContentPackAuthorshipModularInput(ModularInput):
    """
    Modular input that handles Content Pack app creation process
    """

    title = 'IT Service Intelligence Authorship Async Process Queue'
    description = 'Create the content pack app.'
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_authorship_queue'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [{
            'name': 'log_level',
            'title': 'Logging Level',
            'description': 'This is the level at which the modular input will log data.'
        }]

    @skip_run_during_migration
    def do_run(self, input_config):
        '''
        - This is the method called by splunkd when mod input is enabled.
        @param input_config: config passed down by splunkd
        '''
        logger = getLogger4ModInput(input_config)
        if not is_feature_enabled('itsi-content-pack-authorship', self.session_key):
            logger.info('content pack authorship feature not enabled')
            return
        if modular_input_should_run(self.session_key, logger):
            authorship_worker = AuthorshipOperation(self.session_key, logger)
            authorship_worker.run(input_config)


if __name__ == '__main__':
    worker = ItsiContentPackAuthorshipModularInput()
    worker.execute()
    sys.exit(0)
