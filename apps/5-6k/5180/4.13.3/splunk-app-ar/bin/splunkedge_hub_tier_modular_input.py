"""
(C) 2025 Splunk Inc. All rights reserved.

"""

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

import base64
import uuid
import hashlib
import hmac
import json

from splunkar import constants, logging
from splunkar.util.edge import edge_settings_helper
from splunkar.util.modular_input_utils import SplunkARModularInput
from splunkar.services import banner_service

sys.path.remove(make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

LOGGER = logging.get_logger(__name__)


class SplunkEdgeHubTierModularInput(SplunkARModularInput):
    """Modular input to manage service tier in OTI app"""

    title = 'Splunk OTI Tier Manager'
    description = 'Manages the service tier for Splunk OTI'
    app = constants.APP_NAME
    name = 'splunkedge_hub_tier_modular_input'
    input_key = f'{name}://{name}'
    tier_info_key = 'tier_info'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def __init__(self, logger):
        super().__init__(logger)

    def get_installation_uuid(self):
        edge_settings = edge_settings_helper.get_edge_settings(auth_header=self.session_key)
        return uuid.UUID(edge_settings.installation_id)

    def decode_tier_info(self, token: str, installation_uuid: uuid.UUID) -> dict:
        try:
            secret = str(installation_uuid).encode('utf-8')
            decoded = base64.b64decode(token)
            message, _, signature = decoded.partition(b'.')
            expected_sig = hmac.new(secret, message, hashlib.sha256).digest()
            if hmac.compare_digest(signature, expected_sig):
                return json.loads(message.decode('utf-8'))
            else:
                return {}
        except Exception:
            return {}

    def set_trial_tier(self, reason: str):
        self.logger.info(f'oti_tier_manager: {reason}, setting trial tier.')
        banner_service.set_trial_banner_enabled(auth_header=self.session_key, is_enabled=True)

    def set_non_trial_tier(self, tier_name: str):
        self.logger.info(f'oti_tier_manager: {tier_name} tier applied to OTI installation')
        banner_service.set_trial_banner_enabled(auth_header=self.session_key, is_enabled=False)

    def run(self) -> None:
        try:
            self.logger.info('oti_tier_manager: Starting Modular Input')

            # Retrieve input
            inputs = self.inputs.get(self.input_key)
            tier_info = inputs.get(self.tier_info_key)

            # No tier_info means OTI is running on trial mode
            if not tier_info:
                self.set_trial_tier('No tier_info found')
                return

            installation_uuid = self.get_installation_uuid()
            license_details = self.decode_tier_info(tier_info, installation_uuid)

            if not license_details:
                self.set_trial_tier('Invalid tier_info')
                return

            # Validate tier id, right now behavior is the same no matter the tier id
            # Only ids for essentials and advantage are supported
            tier_id = license_details.get('t')
            if tier_id != 1 and tier_id != 2:
                self.set_trial_tier('Unsupported tier')
                return

            tier_name = 'essentials' if tier_id == 1 else 'advantage'
            self.set_non_trial_tier(tier_name)

        except Exception as e:
            self.logger.error(f'oti_tier_manager: Error when running modular input: {e}')


if __name__ == '__main__':
    m = SplunkEdgeHubTierModularInput(LOGGER)
    m.execute()
