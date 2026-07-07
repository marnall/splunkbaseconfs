# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.itoa_config import get_supported_objects
from ITOA.itoa_common import modular_input_should_run, get_object_batch_size
from ITOA.setup_logging import getLogger4ModInput, InstrumentCall
from ITOA.mod_input_utils import skip_run_during_migration
from maintenance_services.maintenance_operations.operative_maintenance_log import OperativeMaintenanceLog

from SA_ITOA_app_common.solnlib.modular_input import ModularInput


class MaintenanceMinderModularInput(ModularInput):
    """
    Mod input dodicated to populate operative maintenance log for maintenance services
    """

    title = "Maintenance Minder Modular Input"
    description = "Maintenance minder to populate operative maintenance log for maintenance services."
    handlers = None
    app = 'SA-ITOA'
    name = 'maintenance_minder'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    maintenance_log_collection = 'operative_maintenance_log'

    def extra_arguments(self):
        return [{
            'name': "log_level",
            'title': "Logging Level",
            'description': "This is the level at which the modular input will log data."
        }]

    @skip_run_during_migration
    def do_run(self, input_config):
        """
        - This is the method called by splunkd when mod input is enabled.

        @type: object
        @param input_config: config passed down by splunkd
        """
        logger = getLogger4ModInput(input_config)
        _instrumentation = InstrumentCall(logger)
        transaction_id = _instrumentation.push("maintenance_minder.do_run", transaction_id=None)

        if not modular_input_should_run(self.session_key, logger=logger):
            logger.info("Will not run modular input on this node.")
            return

        operative_maintenance_log = OperativeMaintenanceLog(self.session_key)
        batch_size = get_object_batch_size(self.session_key, self.maintenance_log_collection)

        try:
            operative_maintenance_log.populate_operative_maintenance_log(
                transaction_id=transaction_id, processing_batch_size=batch_size)
        except Exception as e:
            logger.error(f"Error while populating operative maintenance log: {e}")

        if operative_maintenance_log.is_recurring_maintenance_window_enabled:
            logger.info("Recurring maintenance window feature is enabled. Will update next occurrence dates for recurring maintenance windows.")
            operative_maintenance_log.update_next_occurrences_in_maintenance_calendar(transaction_id=transaction_id)
        else:
            logger.info("Recurring maintenance window feature is not enabled. Will not update next occurrence dates for recurring maintenance windows.")

        _instrumentation.pop("maintenance_minder.do_run", transaction_id)


if __name__ == "__main__":
    worker = MaintenanceMinderModularInput()
    worker.execute()
