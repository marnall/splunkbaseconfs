# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input that runs on startup. It does the following:
1. Initializes HEC on this Search Head.
2. Creates and chowns pertinent HEC tokens.
"""

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
from common_util_hec_initializer import initialize_hec
import itsi_path
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from itsi.itsi_utils import ItsiMacroReader

from SA_ITOA_app_common.solnlib.modular_input import ModularInput


class ITSINotableEventHECInit(ModularInput):
    """
    Class that implements all the required steps. See method `do_run`.
    """

    title = 'IT Service Intelligence HEC Initializer'
    description = 'Initializes Splunk HEC, creates and sets the right ACL values for HEC tokens consumed by ITSI Episode Review.'
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_notable_event_hec_init'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [{
            'name': "log_level",
            'title': "Logging Level",
            'description': ("This is the level at which the modular input will log data; "
                "DEBUG, INFO, WARN, ERROR.  Defaults to WARN.")
        }]

    @skip_run_during_migration
    def do_run(self, input_config):
        """
        This is the method called by splunkd when mod input is enabled.
        It initializes Splunk HEC on this SH and acquires the token.

        @param input_config: config passed down by splunkd
        """
        logger = getLogger4ModInput(input_config)

        # this modular input must run on all search heads in a SHC, so we will
        # not do any SHC specific checks.
        TOKEN = 'token'
        INDEX = 'index'
        HOST = 'host'
        SOURCE = 'source'
        SOURCETYPE = 'sourcetype'
        APP = 'app'
        ISUSEACK = 'is_use_ack'

        itsi_tracked_alerts_macro = ItsiMacroReader(self.session_key, 'itsi_event_management_index_with_close_events')
        itsi_grouped_alerts_macro = ItsiMacroReader(self.session_key, 'itsi_event_management_group_index')
        itsi_notable_audit_macro = ItsiMacroReader(self.session_key, 'itsi_notable_audit_index')
        itsi_notable_archive_macro = ItsiMacroReader(self.session_key, 'itsi_notable_archive_index')

        tokens_info = [
            {
                TOKEN: 'Auto Generated ITSI Event Management Token',
                INDEX: itsi_tracked_alerts_macro.index,
                HOST: None,
                SOURCE: None,
                SOURCETYPE: 'itsi_notable:event',
                APP: 'itsi',
                ISUSEACK: False,
            },
            {
                TOKEN: 'Auto Generated ITSI Notable Event Retention Policy Token',
                INDEX: itsi_notable_archive_macro.index,
                HOST: None,
                SOURCE: None,
                SOURCETYPE: 'itsi_notable:archive',
                APP: 'itsi',
                ISUSEACK: False,
            },
            {
                TOKEN: 'Auto Generated ITSI Notable Index Audit Token',
                INDEX: itsi_notable_audit_macro.index,
                HOST: None,
                SOURCE: 'Notable Event Audit',
                SOURCETYPE: 'itsi_notable:audit',
                APP: 'itsi',
                ISUSEACK: False,
            },
            {
                TOKEN: 'itsi_group_alerts_token',
                INDEX: itsi_grouped_alerts_macro.index,
                HOST: None,
                SOURCE: 'itsi_group_alerts',
                SOURCETYPE: 'itsi_notable:group',
                APP: 'itsi',
                ISUSEACK: False,
            },
            {
                TOKEN: 'itsi_group_alerts_sync_token',
                INDEX: itsi_grouped_alerts_macro.index,
                HOST: None,
                SOURCE: 'itsi_group_alerts',
                SOURCETYPE: 'itsi_notable:group',
                APP: 'itsi',
                ISUSEACK: True,
            },
            {
                TOKEN: 'itsi_group_comments_token',
                INDEX: itsi_grouped_alerts_macro.index,
                HOST: None,
                SOURCE: 'Notable Event Comment',
                SOURCETYPE: 'itsi_notable:comment',
                APP: 'itsi',
                ISUSEACK: False,
            }
        ]
        initialize_hec(self.session_key, logger, tokens_info)


if __name__ == "__main__":
    worker = ITSINotableEventHECInit()
    worker.execute()
