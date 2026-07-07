# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import logging

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from itsi.backfill import ItsiBackfillCore
from ITOA.itoa_common import post_splunk_user_message, modular_input_should_run

from SA_ITOA_app_common.solnlib.modular_input import ModularInput

# Flag used for generating the restartless testing logs only once.
modular_input_reloaded = False


class BackfillModularInputException(Exception):
    pass


class ItsiBackfillModularInput(ModularInput):
    '''
    - Delegate the work to ItsiBackfillCore class

    Mod input does the following:
    1. startup actions:
        - clear completed requests
        - check in-progress jobs and sleep until they complete
        - instantiate JobProcessor classes
    2. backfill loop:
        - retrieve new backfill requests from kv store
        - for every new request, set up BackfillRequestManager and BackfillJobQueue
        - check if JobProcessors are idle and if so, feed them from the queue
    '''

    title = "IT Service Intelligence Backfill Manager"
    description = ("Supervises long-running backfill jobs that generate "
                   "summarized KPI metrics from raw data.")
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_backfill'
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

    def show_message(self, message):
        post_splunk_user_message(message, session_key=self.session_key)

    @skip_run_during_migration
    def do_run(self, stanzas):
        """
        This is the method called by splunkd when mod input is enabled.
        @param stanzas: config stanzas passed down by splunkd
        """
        logger = getLogger4ModInput(stanzas)
        # log the message for restartless upgrade testing which can be useful while debugging.
        global modular_input_reloaded
        if not modular_input_reloaded:
            stanza_name = next(iter(stanzas.keys()))
            logger.info(f"Restartless upgrade - Reloaded modular input {stanza_name}")
            modular_input_reloaded = True

        if not modular_input_should_run(self.session_key, logger=logger):
            logger.info("Modular input will not run on this node.")
            return

        # Single instance mode for safety only, so we only want the first stanza
        stanza_config = next(iter(stanzas.values()))
        level = stanza_config.get("log_level", 'INFO').upper()
        if level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
            level = "INFO"

        logger.setLevel(logging.getLevelName(level))

        # Main Logic
        logger.debug("Running ITSI backfill manager.")

        try:
            backfill_core = ItsiBackfillCore(self.session_key,
                                             modular_input_should_run, messenger=self.show_message, logger=logger)
            backfill_core.start()
        except Exception as e:
            if "Splunkd daemon is not responding: " in str(e) or "ConnectionError" in str(e):
                logger.warning('Backfill core job connection issue. "%s" If this message occurs only once, '
                               'KV store may still be initializing.', e)
            else:
                logger.exception("Backfill core job exception.")

        logger.debug("Exiting modular input.")
        return


if __name__ == "__main__":
    worker = ItsiBackfillModularInput()
    worker.execute()
    sys.exit(0)
