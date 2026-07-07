# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import sys
import logging
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

from ITOA.itoa_common import modular_input_should_run
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from ITOA.setup_logging import getLogger4ModInput
from itsi.duplicate_entities_manager.duplicate_entities_nightly_job_scheduler_job import \
    DuplicateEntitiesNightlyJobSchedulerJob


class ITSIDuplicateEntitiesNightlyJobSchedulerModularInput(ModularInput):
    """
    Modular input responsible enqueuing duplicate entities generation job to the
    itsi_duplicate_entities_job_queue collection once everyday
    It gets invoked 12AM everyday
    cron schedule: "0 0 * * *"
    """
    title = "IT Service Intelligence Duplicate Entities Daily Job Scheduler"
    description = "Enqueues a generation job for generating duplicate entities"
    handler = None
    app = 'SA-ITOA'
    name = 'itsi_duplicate_entities_nightly_job_scheduler'
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
            logger.info("Starting an duplicate entities job scheduler")
            job_scheduler = DuplicateEntitiesNightlyJobSchedulerJob(self.session_key)
            job_scheduler.enqueue_job("NIGHTLY_JOB")
            logger.info("Duplicate entities scheduler mod input completed successfully.")
        else:
            logger.info("Duplicate entities scheduler Job Modular input will not run on this node.")


if __name__ == "__main__":
    worker = ITSIDuplicateEntitiesNightlyJobSchedulerModularInput()
    worker.execute()
    sys.exit(0)
