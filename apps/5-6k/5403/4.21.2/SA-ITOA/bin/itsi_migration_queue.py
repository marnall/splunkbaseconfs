# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

'''
Modular Input that runs on startup if needed and handles migration
scenarios.
'''

import os
import sys
import time
from threading import Thread

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
# make sure itsi_migration_log is first in order, to setup global logger
from itsi.upgrade.itsi_migration_log import getMigrationLogger
from itsi.upgrade.migration_queue_operation import MigrationQueueOperation
from ITOA.itoa_common import modular_input_should_run, get_conf_stanza_single_entry
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from itsi.itsi_utils import ITOAInterfaceUtils
from itsi.upgrade.constants import UPGRADE_TIMEOUT


class ItsiMigratorModularInput(ModularInput):
    '''
    Mod input that handles Upgrades which is primarily migration of data
    from older version to current version
    '''

    title = 'IT Service Intelligence Migration Async Process Queue'
    description = 'Migrates the schemas from the old version to the new version.'
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_migration_queue'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [{
                'name': 'log_level',
                'title': 'Logging Level',
                'description': 'This is the level at which the modular input will log data.'
                }]

    def do_run(self, input_config):
        '''
        - This is the method called by splunkd when mod input is enabled.
        @param input_config: config passed down by splunkd
        '''
        logger = getMigrationLogger()

        if modular_input_should_run(self.session_key, logger):
            try:
                upgrade_timeout = int(get_conf_stanza_single_entry(
                    self.session_key, 'itsi_settings', 'upgrade_timeouts', 'upgrade_timeout').get('content', UPGRADE_TIMEOUT))

                migration_obj = MigrationQueueOperation(self.session_key, logger)
                upgrade_thread = Thread(name='UpgradeThread', target=migration_obj.execute_migration_queue)
                upgrade_thread.start()
                upgrade_thread.join(timeout=upgrade_timeout)
                if upgrade_thread.is_alive():
                    upgrade_timeout_dict = {}
                    upgrade_timeout_dict["message"] = "Could not complete because the upgrade took \
                    too long to complete. Restart the upgrade and try again."
                    upgrade_timeout_dict["timeout"] = upgrade_timeout
                    entry = ITOAInterfaceUtils.get_migration_status_from_kv(
                        self.session_key)
                    ITOAInterfaceUtils.append_data_to_migration_status_kv(self.session_key,
                                                                          entry,
                                                                          is_running=False,
                                                                          end_timestamp=time.time(),
                                                                          has_succeeded=False,
                                                                          upgrade_timeout=upgrade_timeout_dict)
                    # Cleaning the migration queue to stop the automatic re-trigger of upgrade
                    migration_obj.clear_migration_queue()
                    logger.exception("Timeout occurred while upgrading ITSI")
                    # Need to terminate the process for terminate the execution of function run by the thread
                    os._exit(0)
            except Exception as exception:
                logger.error(exception)
                raise Exception(exception)


if __name__ == '__main__':
    worker = ItsiMigratorModularInput()
    worker.execute()
    sys.exit(0)
