# ${copyright}
"""
Enterprise Networking Setup Defaults Modular Input

This modular input runs once when Splunk starts to initialize default
configurations for the Enterprise Networking content pack.
"""

import sys
import time

from splunk.clilib.bundle_paths import make_splunkhome_path
from utils import EnterpriseNetworkingConnectionsUtil, setup_logger

sys.path.append(make_splunkhome_path(['etc', 'apps', 'DA-ITSI-CP-enterprise-networking', 'lib']))

from solnlib.modular_input import ModularInput
from solnlib.server_info import ServerInfo

ITSI_EVENT_MANAGEMENT_INTERFACE_API = "/servicesNS/<user>/<app>/event_management_interface/data_integration"
MAX_RETRIES = 3
RETRY_DELAY = 10


class EnterpriseNetworkingDefaultLoader(ModularInput):
    """
    Modular input for setting up default configurations for the Enterprise Networking content pack.
    This runs once at Splunk startup to initialize necessary defaults.
    """

    title = "Enterprise Networking Default Loader"
    description = "Modular input to set up default alerts configurations for the Enterprise Networking content pack"
    app = "DA-ITSI-CP-enterprise-networking"
    name = "enterprise_networking_default_loader"
    handlers = None
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        """
        Define extra arguments for the modular input.
        :return:
        """
        return [{
            'name': 'log_level',
            'title': 'Logging Level',
            'description': 'This is the level at which the modular input will log data.'
        }]

    def do_run(self, inputs: dict):
        """
        This method is called by Splunk when the modular input is enabled.
        :param inputs:
        :return:
        """
        logger = setup_logger(self.name)
        logger.info("Enterprise Networking Setup Defaults modular input started")

        server_info = ServerInfo(self.session_key)
        # log the message for restartless upgrade testing which can be useful while debugging.
        stanza_name = next(iter(inputs.keys()))
        logger.info("%s modular input running on instance: %s", stanza_name,
                    server_info.server_name)

        # Initialize default configurations
        attempts = 0
        setup_complete = False
        util = EnterpriseNetworkingConnectionsUtil(self.session_key, logger)
        while attempts < MAX_RETRIES and not setup_complete:
            attempts += 1
            try:
                setup_complete = util.setup_connections()
                logger.info(
                    "Enterprise Networking default connections setup attempt=%d success=%s",
                    attempts, setup_complete
                )
            except Exception as err:
                logger.warning("Enterprise Networking setup failed with error=%s", err)

            if not setup_complete:
                time.sleep(RETRY_DELAY * 2 ^ attempts)  # Exponential backoff

        if not setup_complete:
            logger.error(
                "Enterprise Networking default connections setup failed after %d attempts",
                attempts
            )


if __name__ == '__main__':
    loader = EnterpriseNetworkingDefaultLoader()
    loader.execute()
