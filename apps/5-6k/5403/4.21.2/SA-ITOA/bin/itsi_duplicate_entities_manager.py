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
from ITOA.mod_input_utils import skip_run_during_migration
from itsi.duplicate_entities_manager.duplicate_entities_manager_job import DuplicateEntitiesManagerJob


class ITSIDuplicateEntitiesManagerModularInput(ModularInput):
    """
    Modular input responsible for doing the following:
    1. Generating a set of duplicate entities based on aliases/titles
    2. Bulk Remediating entities
    """
    title = "IT Service Intelligence Duplicate Entities Manager"
    description = "Generates a set of duplicate entities based on alias/title OR bulk remediates duplicate entities"
    handlers = None
    app = 'SA-ITOA'
    name = 'duplicate_entities_manager'
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

    @skip_run_during_migration
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
            logger.info("Starting an entities duplicate manager job")
            duplicate_entities_manager = DuplicateEntitiesManagerJob(self.session_key, logger=logger)
            duplicate_entities_manager.kickstart_duplicate_entities_remediation_or_generation_job()
            logger.info("Entity Duplicates Manager Job Modular input completed successfully.")
        else:
            logger.info("Entity Duplicates Manager Job Modular input will not run on this node.")


if __name__ == "__main__":
    worker = ITSIDuplicateEntitiesManagerModularInput()
    worker.execute()
    sys.exit(0)
