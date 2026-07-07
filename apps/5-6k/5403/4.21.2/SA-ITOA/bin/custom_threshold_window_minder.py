# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.itoa_common import modular_input_should_run, get_current_utc_epoch
from ITOA.setup_logging import getLogger4ModInput
from custom_threshold_windows.operative_custom_threshold_log import OperativeCustomThresholdLog
from feature_flagging.license_retriever import LicenseRetriever
from feature_flagging.suite_content import SuiteContent
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from itsi.objects.itsi_backup_restore import ItsiBackupRestore
from ITOA import itoa_refresh_queue_utils


class CustomThresholdMinderModularInput(ModularInput):
    """
    Mod input dedicated to populate operative Custom threshold Window log
    """

    title = "IT Service Intelligence Custom Threshold Windows Modular Input"
    description = "Minder to populate operative Custom Threshold Window log"
    handlers = None
    app = 'SA-ITOA'
    name = 'custom_threshold_window_minder'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    owner = 'nobody'

    def extra_arguments(self):
        return [{
                'name': "log_level",
                'title': "Logging Level",
                'description': "This is the level at which the modular input will log data."}]

    def do_run(self, input_config):
        """
        - This is the method called by splunkd when mod input is enabled.

        @type: object
        @param input_config: config passed down by splunkd
        """
        logger = getLogger4ModInput(input_config)

        license_retriever = LicenseRetriever(self.session_key)
        if license_retriever.get_suite() == SuiteContent.least_permissible_suite():
            logger.warn('Custom threshold windows feature is not enabled')
            return

        restore_running_warning = 'Skipping custom threshold windows modular input since restore job is in-progress'
        refresh_jobs_running_warning = ('Skipping custom threshold windows modular input since refresh '
                                        'job started as part of restore job is in-progress. Refresh Job details: {%s}')

        # TODO: Make the following a decorator like those in mod_input_utils
        # Skip the execution of Modular Input if there is restore operation going on
        itsi_backup_restore_interface = ItsiBackupRestore(self.session_key, self.owner)
        last_48_hours = get_current_utc_epoch() - (3600 * 48)
        filter_backup_restore = {'$and': [
            {'job_type': 'Restore'},
            {'start_time': {'$gt': last_48_hours}},
            {'transaction_id': {'$ne': None}}
        ]}
        backup_restore_jobs = itsi_backup_restore_interface.get_bulk(self.owner,
                                                                     filter_data=filter_backup_restore,
                                                                     fields=['_key', 'transaction_id', 'status'])
        transaction_ids = []
        for job in backup_restore_jobs:
            if job['status'] == 'In Progress':
                logger.warn(restore_running_warning)
                return
            transaction_id = job.get('transaction_id', None)
            if transaction_id is not None:
                transaction_ids.append(transaction_id)

        # Skip the execution of Modular input if there is a job related to restore in refresh queue
        if len(transaction_ids) > 0:
            adapter = itoa_refresh_queue_utils.RefreshQueueAdapter(self.session_key)
            filter_data = {'$or': [
                {'transaction_id': transaction_id}
                for transaction_id in transaction_ids]}
            restore_refresh_jobs = adapter.get_refresh_jobs_by_filter_condition(filter_data=filter_data)

            if len(restore_refresh_jobs) > 0:
                logger.warn(refresh_jobs_running_warning, restore_refresh_jobs)
                return

        if modular_input_should_run(self.session_key, logger):
            OperativeCustomThresholdLog(self.session_key).activate_and_deactivate_ctws()


if __name__ == "__main__":
    worker = CustomThresholdMinderModularInput()
    worker.execute()
