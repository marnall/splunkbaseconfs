# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import logging
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path

from ITOA.itoa_common import modular_input_should_run

from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from ITOA.setup_logging import getLogger4ModInput

from itsi.csv_import.itsi_bulk_import_entities_status_cache_cleanup import EntityStatusCacheCleanup


class ITSIEntitiesStatusCacheCleanup(ModularInput):
    """
    Modular input responsible for entities status cache clean up.
    """
    title = "IT Service Intelligence Entities Status Cache Cleanup"
    description = "Removes the reference of deleted entities from status cache collection"
    handlers = None
    app = 'SA-ITOA'
    name = 'entities_status_cache_cleanup'
    use_single_instance = True
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [
            {
                'name': "log_level",
                'title': "Logging Level",
                'description': "This is the level at which the modular input will log data."
            }
        ]

    def do_run(self, stanzas):
        # First: setup logs
        logger = getLogger4ModInput(stanzas)

        # Single instance mode - we only want the first stanza
        stanza_config = next(iter(stanzas.values()))
        level = stanza_config.get("log_level", 'INFO').upper()
        if level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
            level = "INFO"

        logger.setLevel(logging.getLevelName(level))

        if modular_input_should_run(self.session_key, logger=logger):
            logger.info("Entity status cache clean-up Modular input started successfully.")
            entity_status_cleanup = EntityStatusCacheCleanup(self.session_key, logger=logger)
            entity_status_cleanup.entities_status_cache_cleanup()
            logger.info("Entity status cache clean-up Modular input completed successfully.")
        else:
            logger.info("Entity status cache clean-up Modular input will not run on this node.")


if __name__ == "__main__":
    worker = ITSIEntitiesStatusCacheCleanup()
    worker.execute()
    sys.exit(0)
