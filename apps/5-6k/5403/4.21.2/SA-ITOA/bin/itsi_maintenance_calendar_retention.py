# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import sys
import logging

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common', 'splunklib']))

from SA_ITOA_app_common.solnlib.conf_manager import ConfManager
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from ITOA.storage.itoa_storage import ITOAStorage
from maintenance_services.maintenenance_calendar_retention_policy import MaintenanceCalendarRetentionPolicy
from ITOA.mod_input_utils import skip_run_during_migration
from ITOA.setup_logging import getLogger4ModInput
from ITOA.itoa_common import modular_input_should_run


class ItsiMaintenanceCalendarRetentionModularInput(ModularInput):
    """
    Modular input which cleans up completed and aged Maintenance Calendar Collection entries from kvstore
    collection (maintenance_calendar), used to store all maintenance_calendar objects.
    """
    title = 'IT Service Intelligence Maintenance Calendar Retention'
    description = 'Deletes/Archives the completed and aged Maintenance Calendar Collection entries.'
    app = 'SA-ITOA'
    name = 'itsi_maintenance_calendar_retention'
    owner = 'nobody'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def __init__(self):
        self.retention_config = None
        # Orphan process monitor
        self._orphan_monitor = None

    @skip_run_during_migration
    def do_run(self, input_config):
        """
        This is the method called by splunkd when mod input is enabled.
        @param input_config: input config for mod input
        """

        logger = getLogger4ModInput(input_config)
        self.logger = logger
        stanza_config = next(iter(input_config.values()))

        level = stanza_config.get("log_level", 'INFO').upper()
        if level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
            level = "INFO"
        logger.setLevel(logging.getLevelName(level))

        if not modular_input_should_run(self.session_key, logger=logger):
            logger.info("Will not run modular input on this node")
            return

        self.init_configuration()
        # default retention time to 180 days if not provided
        retention_time_in_days = self.get_configuration_value('retentionTimeInDays', 180)

        # default archival time to 30 days if not provided
        archival_time_in_days = self.get_configuration_value('archivalTimeInDays', 30)

        # default archival state is disabled (1) if not provided
        archival_disabled = self.get_configuration_value('disableArchival', 1)
        archival_batch_size = self.get_configuration_value('batch_size', 500)
        retention_policy = MaintenanceCalendarRetentionPolicy(
            self.session_key, retention_time_in_days, archival_time_in_days, archival_disabled, archival_batch_size,
            logger=logger)

        kvstore = ITOAStorage()
        if kvstore.wait_for_storage_init(self.session_key):
            retention_policy.execute()
        else:
            logger.error(
                'KV Store unavailable for running maintenance calendar retention policy. Exiting.')
            sys.exit(1)

    def init_configuration(self):
        """
        Fetches all the configuration from itsi_maintenance_calendar.conf
        """
        try:
            cfm = ConfManager(self.session_key, 'SA-ITOA')
            conf = cfm.get_conf('itsi_maintenance_calendar')
            self.retention_config = conf.get('retention_settings')
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('Failed to fetch configuration from itsi_maintenance_calendar.conf')

    def get_configuration_value(self, key, default_value):
        if self.retention_config is not None:
            configured_value = self.retention_config.get(key)
            if configured_value is None:
                return default_value
            else:
                return configured_value
        else:
            return default_value


if __name__ == "__main__":
    worker = ItsiMaintenanceCalendarRetentionModularInput()
    worker.execute()
    sys.exit(0)
