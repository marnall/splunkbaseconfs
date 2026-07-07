# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
from ITOA.itoa_common import modular_input_should_run
from ITOA.setup_logging import getLogger4ModInput
from itsi.sandbox.service_sandbox_status_updater import ServiceSandboxStatusUpdater
from SA_ITOA_app_common.solnlib.modular_input import ModularInput


class ServiceSandboxStatusUpdaterModularInput(ModularInput):
    """
    Mod input dedicated to update the Status of Service Sandbox to Edit mode.
    """

    title = "IT Service Intelligence Service Sandbox Status Updater Modular Input"
    description = "Minder to move all the Service Sandbox in Edit mode"
    handlers = None
    app = 'SA-ITOA'
    name = 'service_sandbox_status_updater'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    owner = 'nobody'

    def extra_arguments(self):
        return [{
                'name': "log_level",
                'title': "Logging Level",
                'description': "Level at which log data."}]

    def do_run(self, input_config):
        """
        - This is the method called by splunkd when mod input is enabled.

        @type: object
        @param input_config: config passed down by splunkd
        """
        logger = getLogger4ModInput(input_config)
        logger.debug('ServiceSandboxStatusUpdaterModularInput Invoked')

        if modular_input_should_run(self.session_key, logger):
            ServiceSandboxStatusUpdater(self.session_key).update_service_sandbox_status()


if __name__ == "__main__":
    worker = ServiceSandboxStatusUpdaterModularInput()
    worker.execute()
