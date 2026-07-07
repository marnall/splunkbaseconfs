# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import logging

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
from ITOA.itoa_common import post_splunk_user_message, modular_input_should_run, is_feature_enabled
from ITOA.mod_input_utils import skip_run_during_migration
from itsi.searches.itsi_at_search import ItsiAtSearch
from ITOA.setup_logging import getLogger4ModInput
from ITOA.storage.itoa_storage import ITOAStorage

from SA_ITOA_app_common.solnlib.modular_input import ModularInput

# Flag used for generating the restartless testing logs only once.
modular_input_reloaded = False


class ItsiAtSavedSearchRewriter(ModularInput):
    '''
    Modular input to rewrite AT saved searches based on the feature flags
    itsi-at-outlier-detection and itsi-high-scale-at.
    '''
    title = "IT Service Intelligence AT search rewriter"
    description = "Updates AT saved searches with itsiat/applyat command and high scale AT" \
        "when itsi-at-outlier-detection and/or itsi-high-scale-at flags are switched."
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_at_saved_search_rewriter'
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
        if len(stanzas) == 0:
            # The feature is disabled, no stanzas are present.
            return
        logger = getLogger4ModInput(stanzas)

        # Single instance mode for safety only, so we only want the first stanza
        stanza_name = next(iter(stanzas.keys()))
        stanza_config = next(iter(stanzas.values()))

        # log the message for restartless upgrade testing which can be useful while debugging.
        global modular_input_reloaded
        if not modular_input_reloaded:
            logger.info(f"Restartless upgrade - Reloaded modular input {stanza_name}")
            modular_input_reloaded = True

        if not modular_input_should_run(self.session_key, logger=logger):
            logger.info("Modular input will not run on this node.")
            return

        level = stanza_config.get("log_level", 'INFO').upper()
        if level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
            level = "INFO"

        logger.setLevel(logging.getLevelName(level))

        logger.info("Running itsi_at_saved_search_rewriter modular input.")

        is_high_scale_at_enabled = is_feature_enabled('itsi-high-scale-at', self.session_key)
        is_entity_level_at_enabled = is_feature_enabled('itsi-entity-level-adaptive-thresholding', self.session_key)

        ck = self.checkpointer
        stored_high_scale_at_feature_status_key = stanza_name + 'id' + 'itsi-high-scale-at'
        stored_high_scale_at_feature_status = bool(ck.get(stored_high_scale_at_feature_status_key))

        stored_entity_level_at_feature_status_key = stanza_name + 'id' + 'itsi-entity-level-adaptive-thresholding'
        stored_entity_level_at_feature_status = bool(ck.get(stored_entity_level_at_feature_status_key))

        # Only run Mod Input if checkpoint value and feature flag value doesn't match
        # Mod input for entity Level AT should only run if High Scale AT is enabled
        if (is_high_scale_at_enabled == stored_high_scale_at_feature_status):
            if stored_entity_level_at_feature_status == is_entity_level_at_enabled:
                logger.info("Feature flags for High Scale AT and Entity Level AT were not updated. No need to rewrite AT saved searches.")
                return
            elif not is_high_scale_at_enabled:
                logger.error("High Scale AT is disabled. Cannot start process for Entity Level AT feature flip.")
                raise

        if not is_high_scale_at_enabled and is_entity_level_at_enabled:
            logger.error("Only High Scale AT feature flag disabled. Please also Disable Entity Level AT feature flag to proceed")
            raise

        kvstore = ITOAStorage()
        if not kvstore.wait_for_storage_init(self.session_key):
            raise Exception("KVStore not initialized. Savedsearch rewriter for High Scale AT and Entity Level AT failed.")

        try:
            # Call utility method to convert saved searches
            failed_searches = ItsiAtSearch(self.session_key).rewrite_saved_searches(is_high_scale_at_enabled=is_high_scale_at_enabled, is_entity_level_at_enabled=is_entity_level_at_enabled)
            if len(failed_searches) == 0:
                logger.info("AT saved searches were rewritten successfully.")
                ck.update(stored_high_scale_at_feature_status_key, int(is_high_scale_at_enabled))
                ck.update(stored_entity_level_at_feature_status_key, int(is_entity_level_at_enabled))
            else:
                logger.info("AT saved searches rewrite failed for searches: %s" % failed_searches)
        except Exception as e:
            logger.exception("AT saved searches rewrite failed with an exception: %s ", e)

        logger.info("Exiting itsi_at_saved_search_rewriter modular input.")
        return


if __name__ == "__main__":
    worker = ItsiAtSavedSearchRewriter()
    worker.execute()
    sys.exit(0)
