# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import logging

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITSI-Licensechecker', 'lib']))
sys.path.append(
    make_splunkhome_path(
        [
            "etc",
            "apps",
            "SA-ITSI-Licensechecker",
            "lib",
            "SA_ITSI_Licensechecker_app_common",
        ]
    )
)
from license_manager import LicenseManager
from splunk_licenses_api import SplunkLicensesAPI
from itsi_internal_licenses_group_factory import ItsiInternalLicensesGroupFactory
from utils import setup_logging, modular_input_should_run

from SA_ITSI_Licensechecker_app_common.solnlib.modular_input import ModularInput


class LicenseCheckModularInput(ModularInput):
    title = 'IT Service Intelligence license checker'
    description = 'Checks if Splunk instance has a valid IT Service Intelligence license.'
    handlers = None
    app = "SA-ITSI-Licensechecker"
    name = "itsi_license_checker"
    use_single_instance = True
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [
            {
                'name': 'app_name',
                'title': 'Application name',
                'description': 'Application name, defaults to itsi.'
            },
            {
                'name': 'log_level',
                'title': 'Logging Level',
                'description': 'This is the level at which the modular input will log data.'
            }

        ]

    def do_run(self, stanzas):
        """
        @type stanzas: dict
        @param stanzas: config for this modular input
        """

        # Single instance mode - we only want the first stanza
        stanza = next(iter(stanzas.values()))

        level = stanza.get("log_level", 'INFO').upper()
        if level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
            level = "INFO"

        logger = setup_logging(log_file='itsi_license_checker.log', level=logging.getLevelName(level))

        logger.setLevel(level)
        logger.info('Modular input is starting...')

        if not modular_input_should_run(self.session_key, logger=logger):
            logger.info('Modular input exits: will not run modular input on this node')
            return

        self.app = stanza.get('app_name', 'itsi')

        license_api = SplunkLicensesAPI(self.server_uri, self.session_key, self.app)

        try:
            if license_api.is_license_dependent():
                logger.info(
                    ('Modular input exits: this instance is license dependent. '  # noqa
                     'Will only run on self-licensed or LM node'))
                return
        except Exception:
            logger.exception("Failed to determine license dependency status")
            raise

        logger.info('Modular input is running...')

        try:
            license_group = ItsiInternalLicensesGroupFactory(license_api).get_license_group()
        except Exception:
            logger.exception("Failed to get ITSI internal license group")
            raise

        try:
            manager = LicenseManager(license_api, license_group)
            if not manager.internal_license_installed():
                logger.info('Internal ITSI license is not installed. Installing it...')
                manager.install_internal_license()
                logger.info('Internal ITSI license is installed.')
        except Exception:
            logger.exception("Failed to install internal ITSI license")
            raise

        try:
            manager.manage_plus_license_marker()
        except Exception:
            logger.exception("Error when managing Plus license marker")
            raise

        try:
            manager.manage_license_expiration_signaling_license()
        except Exception:
            logger.exception("Error when managing Expired marker license")
            raise

        logger.info('Modular input completed successfully')


if __name__ == "__main__":
    worker = LicenseCheckModularInput()
    worker.execute()
    sys.exit(0)
