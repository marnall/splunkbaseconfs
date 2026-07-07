# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import logging
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

from ITOA.itoa_common import modular_input_should_run

from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from ITOA.setup_logging import getLogger4ModInput
from feature_flagging.license_retriever import LicenseRetriever
from feature_flagging.ui_view_access_enforcer import UIViewAccessEnforcer
from feature_flagging.itsi_application_renamer import ITSIApplicationRenamer
from feature_flagging.itsi_event_grouping import ItsiEventGrouping


class ITSISuiteEnforcer(ModularInput):
    """
    Modular input responsible for enforcing ITSI suite.
    """
    title = "IT Service Intelligence Suite Enforcer"
    description = "Enforces IT Service Intelligence suite"
    handlers = None
    app = 'SA-ITOA'
    name = 'suite_enforcer'
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
        license_retriever = LicenseRetriever(self.session_key)

        if modular_input_should_run(self.session_key, logger=logger):
            logger.info("Modular input started successfully.")

            try:
                license_retriever.sync_suite_state()
            except Exception:
                logger.exception("Failed to synchronize suite state")
                raise

            try:
                features, suite = license_retriever.get_features_and_suite()
            except Exception:
                logger.exception("Failed to retrieve features and suite")
                raise

            try:
                features = license_retriever.get_features(suite)
                UIViewAccessEnforcer(self.session_key, features).set_view_access()
            except Exception:
                logger.exception("Failed to enforce access on UI views")

            try:
                features = license_retriever.get_features(suite)
                ItsiEventGrouping(self.session_key, features).manage_disable_or_enable()
            except Exception:
                logger.exception("Failed to enable or disable itsi_event_grouping")

        else:
            logger.info("Modular input will not run on this node.")

        try:
            suite = license_retriever.get_suite()
            features = license_retriever.get_features(suite)
            ItsiEventGrouping(self.session_key, features).manage_nats_server()
        except Exception:
            logger.exception("Failed to enable or disable nats server")

        try:
            suite = license_retriever.get_suite()
            ITSIApplicationRenamer(self.session_key, suite).rename()
        except Exception:
            logger.exception("Failed to rename application")


if __name__ == "__main__":
    worker = ITSISuiteEnforcer()
    worker.execute()
    sys.exit(0)
