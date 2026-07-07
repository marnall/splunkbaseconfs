"""
(C) 2020 Splunk Inc. All rights reserved.

Modular Input for processing drone mode subscriptions
"""
import sys
import os
import http
import asyncio
import warnings

warnings.filterwarnings('ignore', '.*service_identity.*', UserWarning)

from splunk.clilib.bundle_paths import make_splunkhome_path

os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
sys.path.append(make_splunkhome_path(['etc', 'apps', 'splunk_app_tv', 'lib']))


from secure_gateway_sdk.util.errors import SpacebridgeApiRequestError
from secure_gateway_sdk.util.splunk_utils.modular_input_utils import modular_input_should_run
from cloudgateway.private.sodium_client import SodiumClient
from cloudgateway.splunk.encryption import SplunkEncryptionContext
from cloudgateway.private.websocket.parent_process_monitor import ParentProcessMonitor
from solnlib import modular_input
from splunk_tv.util.logging import get_logger
from splunk import rest
from splunk_tv.subscriptions.subscription_requests import build_cert_dict
from splunk_tv.kvstore.kvstore import KVStoreFactory
from splunk_tv.rest.request_helpers import get_drone_mode_users, get_drone_mode_tvs
from splunk_tv.util import constants
from splunk_tv.util.string_utils import urlsafe_b64_to_b64
from splunk_tv.util.cert_generator import delete_certificate_data
from splunk_tv.subscriptions.drone_mode_subscription_manager import DroneModeSubscriptionManager

FIVE_MINUTES = 300
FIVE_SECONDS = 5

class MaxIterationsReached(Exception):
    """
    Exception to raise when maximum number of iterations for
    the modular input has been reached
    """


async def run_subscription_manager(encryption_context, session_key, input_config, logger):
    """
     Runs the drone mode subscription manager which updates the ipads/tvs as well as
     keeps the tls certificate bundle up to date

    :param encryption_context:
    :param session_key:
    :param input_config:
    :param logger:
    :return:
    """
    loop_count = 0
    while True:
        try:
            logger.debug(f"Running Drone Mode Subscription Manager modular input loop={loop_count}")
            loop_count += 1
            subscription_manager = DroneModeSubscriptionManager(
                input_config=input_config,
                encryption_context=encryption_context,
                session_key=session_key,
                parent_process_monitor=ParentProcessMonitor(),
            )
            subscription_manager.run()
            await asyncio.sleep(10)
            if loop_count > 360:
                raise MaxIterationsReached
        except MaxIterationsReached as e:
            logger.exception('Max iterations reached. Restarting modular input')
            raise e
        except Exception as e:
            logger.exception('Failed subscription manager')
            raise e


class DroneModeSubscriptionModularInput(modular_input.ModularInput):
    """
    Main entry for processing Drone Mode Subscriptions
    """
    title = 'Splunk App for TV Drone Mode Subscription Processor'
    description = ('Clean up expired subscriptions, and '
                   'send data through Splunk Secure Gateway send message api')
    app = 'splunk_app_tv'
    name = 'drone_mode_subscription_modular_input'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    logger = get_logger(logger_name='drone_mode_modular_input')


    def do_run(self, input_config):
        """
        This will spin up a drone mode subscription manager and begins the reactor loop
        :param input_config:
        :return:
        """
        if not modular_input_should_run(self.session_key, self.logger):
            self.logger.debug("Modular input will not run on this node.")
            return

        self.logger.debug("Starting Drone Mode subscription modular input")

        try:
            sodium_client = SodiumClient(self.logger.getChild('sodium_client'))
            encryption_context = SplunkEncryptionContext(self.session_key,
                                                         constants.CORE_SPLAPP_APP_NAME,
                                                         sodium_client)

            self.logger.debug("Running Drone Mode Subscription Manager modular input")
            task1 = run_subscription_manager(encryption_context,
                                             self.session_key,
                                             input_config,
                                             self.logger)

            asyncio.get_event_loop().run_until_complete(asyncio.wait([task1], return_when=asyncio.FIRST_EXCEPTION))
        except MaxIterationsReached as e:
            self.logger.exception('Maximum iterations reached, restarting input')
            raise e
        except Exception as e:
            self.logger.exception('An error occurred running the drone mode subscription modular input')
            raise e


if __name__ == "__main__":
    worker = DroneModeSubscriptionModularInput()
    worker.execute()
