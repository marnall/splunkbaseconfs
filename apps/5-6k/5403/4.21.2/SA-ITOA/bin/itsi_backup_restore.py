# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from itsi.backup_restore import itsi_backup_restore_utils
from ITOA.storage.itoa_storage import ITOAStorage
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from SA_ITOA_app_common.solnlib.server_info import ServerInfo


class ItsiBackupRestoreModularInput(ModularInput):
    """
    Mod input dedicated to populate operative maintenance log for maintenance services
    """

    title = 'IT Service Intelligence Backup Restore Jobs Processor'
    description = 'Runs backup and restore jobs.'
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_backup_restore'
    use_single_instance = False
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
    def do_run(self, input_config):
        """
        This is the method called by splunkd when mod input is enabled.

        @type: object
        @param input_config: config passed down by splunkd
            input_config is a dictionary key'ed by the name of the modular
            input, its value is the modular input configuration.
        """

        # input_config is a dictionary key'ed by the name of the modular
        # input, its value is the modular input configuration.
        logger = getLogger4ModInput(input_config)  # noqa F841
        input_config = list(input_config.values())[0]
        level = input_config.get('log_level', 'WARN').upper()
        if level not in ("ERROR", "WARN", "WARNING", "INFO", "DEBUG"):
            level = "INFO"

        info = ServerInfo(self.session_key)
        self.jobs_processor = itsi_backup_restore_utils.ITSIBackupRestoreJobsProcessor(
            self.session_key,
            info,
            log_level=level
        )
        if info.is_shc_member():
            self.jobs_processor.logger.info(
                'Running modular input on shc member with search_head_id %s',
                info.guid
            )

        # Wait for KV Store to initialize or we will accidentally clean up deleted jobs
        kvstore = ITOAStorage()
        if kvstore.wait_for_storage_init(self.session_key):
            self.jobs_processor.logger.debug('Running ITSI Backup Restore Jobs Processor.')
            processed_job_count = self.jobs_processor.run()
            self.jobs_processor.logger.debug('Modular input process exiting after processing %s jobs.', processed_job_count)
        else:
            self.jobs_processor.logger.error('KV store unavailable for backup restore agent, exiting. '
                                             'Splunk will restart jobs processor based on modular input interval.')
            sys.exit(1)


if __name__ == "__main__":
    worker = ItsiBackupRestoreModularInput()
    worker.execute()
    sys.exit(0)
