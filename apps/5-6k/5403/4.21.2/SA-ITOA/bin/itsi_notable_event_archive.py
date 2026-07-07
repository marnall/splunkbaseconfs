# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Modular Input which moves events from KV Store to Index
"""

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.itoa_common import modular_input_should_run
from ITOA.setup_logging import getLogger4ModInput
from ITOA.mod_input_utils import skip_run_during_migration
from itsi.event_management.itsi_notable_event_retention_policy import ItsiNotableEventRetentionPolicy

from SA_ITOA_app_common.solnlib.modular_input import ModularInput


class ItsiNotableEventArchiveModularInput(ModularInput):
    """
    Mod input which move events from kv store collection to index
    """

    title = "IT Service Intelligence notable event archiver"
    description = "Moves notable events from the KV store to the index based upon retention policy."
    handlers = None
    app = 'SA-ITOA'
    name = 'itsi_notable_event_archive'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [{
            'name': "owner",
            'title': "Namespace",
            'description' : "Namespace under which the KV store operation is called. Default is 'nobody'."
        }]

    @skip_run_during_migration
    def do_run(self, input_config):
        """
        This is the method called by splunkd when mod input is enabled.
        @param stanzas: stanza
        """
        logger = getLogger4ModInput(input_config)

        if not modular_input_should_run(self.session_key, logger=logger):
            logger.info("Will not run modular input on this node")
            return

        input_config = list(input_config.values())[0]

        if isinstance(input_config, dict):
            owner = input_config.get('owner', 'nobody')
        else:
            owner = 'nobody'

        ItsiNotableEventRetentionPolicy(self.session_key, owner=owner).execute()


if __name__ == "__main__":
    worker = ItsiNotableEventArchiveModularInput()
    worker.execute()
    sys.exit(0)
