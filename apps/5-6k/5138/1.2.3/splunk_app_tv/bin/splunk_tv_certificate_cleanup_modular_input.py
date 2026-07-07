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
from solnlib import modular_input
from splunk_tv.util.logging import get_logger
from splunk import rest
from splunk_tv.subscriptions.subscription_requests import build_cert_dict
from splunk_tv.kvstore.kvstore import KVStoreFactory
from splunk_tv.rest.request_helpers import get_drone_mode_users, get_drone_mode_tvs
from splunk_tv.util import constants
from splunk_tv.util.string_utils import urlsafe_b64_to_b64
from splunk_tv.util.cert_generator import delete_certificate_data

FIVE_MINUTES = 300
FIVE_SECONDS = 5


async def clean_stale_certificate_data(authtoken, logger):
    """
    This function cleans out data from /storage/passwords of
    devices that aren't captains.
    :param authtoken: Used to authenticate with storage/passwords
    :param logger: Used to log request
    :return:

    Function
    """
    retry_count = 0
    kvstore = KVStoreFactory(
        user=constants.NOBODY,
        uri=rest.makeSplunkdUri(),
        logger=logger,
        session_key=authtoken,
        system_session_key=authtoken
    )

    while True:
        try:
            # Since tv configs are namespaced by user, we need to first fetch valid drone mode users
            #
            response_code, users = get_drone_mode_users(kvstore)

            if response_code != http.HTTPStatus.OK:
                raise SpacebridgeApiRequestError('unable to fetch user list',
                                                 status_code=response_code)
            device_ids = list(build_cert_dict(kvstore.system_session_key).keys())

            for user in users:
                # fetch tvs for each user that have the keys we want
                tvs = get_drone_mode_tvs(kvstore, device_ids, user=user)
                # iterate over them and remove keys that are active drone mode captains
                for tv in tvs:
                    device_id = urlsafe_b64_to_b64(tv[constants.KEY])
                    if tv.get(constants.CAPTAIN_ID) == device_id:
                        device_ids.remove(device_id)

            # there is a small potential for a race condition here if somehow a device stops becoming captain
            # between the above for loop and the below deletion, but the net effect of this happening is
            # that the certificate data will be cleaned during the next loop

            # Any keys that are left, we remove data for them in /storage/passwords
            for device_id in device_ids:
                delete_certificate_data(kvstore.system_session_key, device_id)


            # if call succeeds, break out of while loop
            break

        except Exception as e:
            retry_count += 1
            logger.exception(f'Failed to cleanup cert data. Retrying with retry_count={retry_count}')
            await asyncio.sleep(FIVE_SECONDS)
            if retry_count > 2:
                raise e

class CertificateCleanupModularInput(modular_input.ModularInput):
    """
    Modular Input to clean up certificate data every 5 minutes
    """
    title = 'Splunk App for TV Certificate Cleanup'
    description = ('Clean up expired certificate data')
    app = 'splunk_app_tv'
    name = 'certificate_cleanup_modular_input'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    logger = get_logger(logger_name='certificate_cleanup_modular_input')


    def do_run(self, input_config):
        """
        This will spin up a drone mode subscription manager and begins the reactor loop
        :param input_config:
        :return:
        """
        if not modular_input_should_run(self.session_key, self.logger):
            self.logger.debug("Modular input will not run on this node.")
            return

        self.logger.debug("Starting Drone Mode Certificate Cleanup modular input")

        try:
            self.logger.debug("Running Certificate Cleanup modular input")
            task1 = clean_stale_certificate_data(self.session_key, self.logger)

            asyncio.get_event_loop().run_until_complete(asyncio.wait([task1], return_when=asyncio.FIRST_EXCEPTION))

        except Exception as e:
            self.logger.exception('An error occurred running the drone mode subscription modular input')
            raise e


if __name__ == "__main__":
    worker = CertificateCleanupModularInput()
    worker.execute()
