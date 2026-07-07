# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input that runs on startup and load default ACL to KV store
if it is not available
"""

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from itsi.event_management.utils import CorrelationSearchDefaultAclLoader
from ITOA.itoa_common import modular_input_should_run
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from SA_ITOA_app_common.solnlib.server_info import ServerInfo


class ItsiCorrelationSearchAclLoader(ModularInput):
    """
    Mod input that handles Upgrades which is primarily migration of data
    from older version to current version
    """

    title = "IT Service Intelligence Default Correlation Search ACL loader"
    description = "Loads the default correlation search ACL."
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_default_correlation_search_acl_loader'
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
        server_info = ServerInfo(self.session_key)
        # log the message for restartless upgrade testing which can be useful while debugging.
        stanza_name = next(iter(input_config.keys()))
        logger.info(f"Restartless upgrade - Reloaded modular input {stanza_name}")
        logger.info(f"Modular input running on instance: {server_info.server_name}")
        try:
            CorrelationSearchDefaultAclLoader(self.session_key, logger).default_acl_loader()
            logger.info("Successfully set acl for default correlation searches")
        except Exception as e:
            logger.error("Failed to set acl for default correlation searches")
            logger.exception(e)
            raise


if __name__ == "__main__":
    worker = ItsiCorrelationSearchAclLoader()
    worker.execute()
