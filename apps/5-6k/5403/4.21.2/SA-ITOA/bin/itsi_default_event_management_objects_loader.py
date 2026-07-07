# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input that runs on startup that:
 - loads default policies to KV store if they are not available
 - creates default Data Integrations connections if they don't exist
"""

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from ITOA.itoa_config import get_supported_objects
from itsi.event_management.utils import DefaultDataIntegrationConnectionLoader
from itsi.event_management.utils import NotableEventDefaultPoliciesLoader
from ITOA.itoa_common import modular_input_should_run
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration

from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from SA_ITOA_app_common.solnlib.server_info import ServerInfo


class ItsiEventManagementObjectsLoader(ModularInput):
    """
    Mod input that handles Upgrades which is primarily migration of data
    from older version to current version
    """

    title = "IT Service Intelligence Default Event Management Objects Loader"
    description = "Loads the default aggregation policies and creates default data integration connections."
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_default_event_management_objects_loader'
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
        logger.info(f"{stanza_name} modular input running on instance: {server_info.server_name}")
        try:
            ret = NotableEventDefaultPoliciesLoader(self.session_key, logger).upload_default_policies()
            if not ret:
                logger.error('Failed to create default aggregation policies')
            else:
                logger.info("Successfully uploaded default aggregation policies")

            ret = DefaultDataIntegrationConnectionLoader(self.session_key, logger).create_default_data_integration_connections()
            if not ret:
                logger.error("Failed to create one or more default data integration connections")
            else:
                logger.info("Successfully created all default data integration connections")

        except Exception as e:
            logger.exception(e)
            raise


if __name__ == "__main__":
    worker = ItsiEventManagementObjectsLoader()
    worker.execute()
