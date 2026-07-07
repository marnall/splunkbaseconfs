# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input which delete exported csv files after period of time
"""
import json
import sys
import splunk.rest as rest
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
from ITOA.itoa_common import modular_input_should_run, get_itsi_event_management_conf_field_value, get_current_utc_epoch
from ITOA.itoa_object import CRUDMethodTypes
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from SA_ITOA_app_common.solnlib.modular_input import ModularInput


class ItsiExportedEpisodeCleanerModularInput(ModularInput):
    """
    Mod input which move events from kv store collection to index
    """

    title = 'IT Service Intelligence Clean Exported Episode Files'
    description = 'Delete exported episode files.'
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_exported_episode_files_cleaner.py'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    day_to_delete = 7

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
        @param stanzas: stanza
        """
        try:
            logger = getLogger4ModInput(input_config)
            if not modular_input_should_run(self.session_key, logger=logger):
                logger.info('Will not run modular input on this node')
                return
            days_to_delete = get_itsi_event_management_conf_field_value(self.session_key, 'export_csv', 'delete_period')
            if not days_to_delete or not isinstance(days_to_delete, int):
                logger.error('Invalid value for days_to_delete')
                days_to_delete = self.day_to_delete
                logger.info('Setting days to delete default value %s', self.day_to_delete)

            created_time = get_current_utc_epoch() - days_to_delete * 24 * 60 * 60
            getargs = {
                'filter_data': json.dumps({'created_time': {'$lte': created_time}}),
                'output_mode': 'json'
            }
            response, _ = rest.simpleRequest('/servicesNS/nobody/SA-ITOA/event_management_interface/episode_export',
                                             sessionKey=self.session_key,
                                             getargs=getargs,
                                             method=CRUDMethodTypes.METHOD_DELETE)
            if response.status != 204:
                logger.error('Error while deleting episode export with error %s', response)
        except Exception as e:
            logger.exception('Exception occurred while cleaning up the episode export files :  %s', e)


if __name__ == "__main__":
    worker = ItsiExportedEpisodeCleanerModularInput()
    worker.execute()
    sys.exit(0)
