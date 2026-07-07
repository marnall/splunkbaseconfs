"""
(C) 2023 Splunk Inc. All rights reserved.

"""

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

from typing import List
import requests
import time
import base64
from concurrent import futures
from http import HTTPStatus
from splunkar import constants
from splunkar import logging
from splunkar import kvstore
from splunkar.db import hub as hub_db
from splunkar.model.hub import Hub, HubSpacebridgeStatus
from splunkar.util.modular_input_utils import SplunkARModularInput
from splunkar.util import config

sys.path.remove(make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

LOGGER = logging.get_logger(__name__)

MAX_WORKERS = 10


class SplunkEdgeHubStatusModularInput(SplunkARModularInput):
    """Modular input to perform pulse logic for Edge Hub devices"""

    title = 'Edge Hub Status'
    description = 'Edge Hub Status'
    app = constants.APP_NAME
    name = 'splunkedge_hub_status_modular_input'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def __init__(self, logger):
        super().__init__(logger)

    def run(self) -> None:
        t1 = time.time()
        self.config = config.get_app_config()
        self.logger.debug('Starting Edge Hub Status Modular Input')
        hubs = self.get_registered_hubs()
        self.update_connection_status(hubs)
        self.logger.debug(f"Edge Hub Status Modular Input finished in {time.time() - t1}s")

    def get_registered_hubs(self):
        return hub_db.load_all_hubs(self.session_key)

    def update_connection_status(self, hubs: List[Hub]):
        """
        Update's Hub connection status based on connection to Spacebridge server
        """
        if self.config.spacebridge_hostname is None:
            self.logger.error('No spacebridge server endpoint')
            return

        with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(self.update_hub_connection_status, hubs)

    def update_hub_connection_status(self, hub: Hub):
        device_id = base64.b64decode(hub.spacebridge_device_id).hex()
        response = requests.get(
            url=f'https://{self.config.spacebridge_hostname}/status/connection',
            params={'client_id': device_id},
            timeout=self.config.request_timeout_seconds,
        )
        if response.status_code != HTTPStatus.OK:
            self.logger.error('Failed to get connection status for hub: {}. Error: {}'.format(hub.name, response.text))
            return

        prev_status = HubSpacebridgeStatus(hub.spacebridge_status)

        connected = response.json().get('connected')
        hub.spacebridge_status = HubSpacebridgeStatus.CONNECTED if connected else HubSpacebridgeStatus.DISCONNECTED
        hub.spacebridge_status_date = str(round(time.time()))

        try:
            hub_db.update_hub(self.session_key, hub)
            if prev_status != hub.spacebridge_status:
                self.logger.info(
                    f'Hub {hub.name} connection status changed from {prev_status} to {hub.spacebridge_status}'
                )
        except (kvstore.errors.DocumentConflictException, kvstore.errors.DocumentNotFoundException) as e:
            self.logger.error(f"Failed to update Hub connection status: {e}")
        except Exception as e:
            self.logger.error(f"Unknown Error while updating Hub connection status: {e}")


if __name__ == '__main__':
    m = SplunkEdgeHubStatusModularInput(LOGGER)
    m.execute()
