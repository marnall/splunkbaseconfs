# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

from ITOA.itoa_common import modular_input_should_run, is_feature_enabled

from itsi.itsi_version_compare import VersionComparison
from itsi.itsi_utils import ITOAInterfaceUtils
from itsi.upgrade.rename_re_log_files import RenameRELogFiles
# make sure itsi_migration_log is first in order, to setup global logger
from itsi.upgrade.java_file_fixer import JavaFileFixer
from itsi.itoa_rest_interface_provider.itoa_rest_interface_provider import ItoaInterfaceProvider
from SA_ITOA_app_common.solnlib.modular_input import ModularInput

from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration


class ConfigureITSI(ModularInput):
    """
    Just a basic modular input responsible for configuring ITSI.
    Here are just one of the many amazing things it does
        - Import entities from the conf file system into the statestore

    """
    title = "IT Service Intelligence Configurator"
    description = "Configures IT Service Intelligence"
    handlers = None
    app = 'SA-ITOA'
    name = 'configure_itsi'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def __init__(self):
        # Since logger is used before do_run is called, initialize logger first:
        super (ConfigureITSI, self).__init__()

    def extra_arguments(self):
        return [
            {
                'name': "log_level",
                'title': "Logging Level",
                'description': "This is the level at which the modular input will log data."
            },
            {
                'name': "is_configured",
                'title': "Configuration flag",
                'description': "Old configuration"
            }
        ]

    @skip_run_during_migration
    def do_run(self, input_config):
        """
        First part, we need to find the ITSI stanzas, and then move them into the statestore
        The stanzas are just organized by type (entity, kpi, service) etc.  We are just going
        to do a 1:1 import into the statestore
        """
        logger = getLogger4ModInput(input_config)
        # log the message for restartless upgrade testing which can be useful while debugging.
        stanza_name = next(iter(input_config.keys()))
        logger.info(f"Restartless upgrade - Reloaded modular input {stanza_name}")
        # rename the rules engine log files
        try:
            rename_re_log_files = RenameRELogFiles(self.session_key, logger=logger)
            rename_re_log_files.run()
        except Exception:
            logger.exception('Failed to rename Rules Engine log file(s) on the search head.')
        try:
            java_fixer = JavaFileFixer(self.session_key, logger=logger)
            java_fixer.run()
        except Exception:
            logger.exception('Failed to run the Java archive file fixer on the search head.')

        if not modular_input_should_run(self.session_key, logger=logger):
            logger.info("Modular input will not run on this node.")
            return
        version_compare = VersionComparison()
        should_migrate = version_compare.should_render_migration_page(self.session_key)
        # if migrate, configure itsi along with migration process(upgrade/itsi_migration.py)
        if should_migrate:
            logger.info((
                'Migration pending. Exiting configure ITSI modular input as configuration'
                'will be handled by the migration process at the end'
            ))
            return
        # if not migrate, configure itsi with modular input
        ITOAInterfaceUtils.configure_version(self.session_key)
        ITOAInterfaceUtils.configure_team(self.session_key)
        ITOAInterfaceUtils.configure_itsi(self.session_key, logger)
        if is_feature_enabled('itsi-bulk-delete-retired-entities', self.session_key):
            ItoaInterfaceProvider.get_and_post_itsi_retired_entity_delete_status(self.session_key,
                                                                                 'nobody',
                                                                                 'entity',
                                                                                 is_restart=True)
        ITOAInterfaceUtils.configure_in_operator_support(self.session_key)
        # By default there should not be any enabled real time saved search
        # To resolve the https://splunk.atlassian.net/browse/ITSI-20861 app-inspect failure
        # itsi_event_grouping saved search is enabled if there is not entry in local conf
        ITOAInterfaceUtils.enable_itsi_event_grouping(self.session_key, logger)
        # The below function needs to be added in itsi_migration.py as well
        # This code is not executed during ITSI upgrade scenario as function returns from should_migrate check
        # Added function here for fresh installation of ITSI
        ITOAInterfaceUtils.update_itsi_cp_saved_searches_collection(self.session_key, logger)


if __name__ == "__main__":
    worker = ConfigureITSI()
    worker.execute()
    sys.exit(0)
