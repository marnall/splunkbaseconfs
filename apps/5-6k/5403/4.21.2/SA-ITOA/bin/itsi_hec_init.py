# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input that runs on startup. It does the following:
1. Initializes HEC on this Search Head.
2. Creates and chowns pertinent HEC tokens.
"""

import sys
from common_util_hec_initializer import initialize_hec
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from itsi.itsi_utils import ItsiMacroReader

from SA_ITOA_app_common.solnlib.modular_input import ModularInput


class ITSIHECInit(ModularInput):
    """
    Class that implements all the required steps. See method `do_run`.
    """

    title = 'ITSI HEC Initializer for Bulk Import'
    description = 'Initializes Splunk HEC, creates and sets the right ACL values for HEC tokens consumed by Bulk Import.'
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_hec_init'
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

        itsi_import_objects_macro = ItsiMacroReader(self.session_key, 'get_itsi_import_objects_index')

        tokens_info = [{
            TOKEN: 'itsi_bulk_import_token',
            INDEX: itsi_import_objects_macro.index,
            HOST: None,
            SOURCE: 'itsi bulk import',
            SOURCETYPE: 'itsi_import_objects:csv',
            APP: 'itsi',
            ISUSEACK: False,
        }]
        initialize_hec(self.session_key, logger, tokens_info)


if __name__ == "__main__":
    worker = ITSIHECInit()
    worker.execute()
