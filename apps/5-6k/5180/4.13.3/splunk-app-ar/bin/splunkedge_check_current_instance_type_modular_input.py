"""
(C) 2022 Splunk Inc. All rights reserved.

Modular Input for determining and updating config with current environment
"""
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

from http import HTTPStatus
from splunkar import constants
from splunkar import logging
from splunkar import httplib
from splunkar.util import config, general_requests, splunkd_requests
from splunkar.util.config import InstanceType
from splunkar.util.modular_input_utils import SplunkARModularInput
from typing import Tuple, Optional

sys.path.remove(make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

LOGGER = logging.get_logger(__name__)

NOAH_SERVICE_ENDPOINT_PATH = 'services/configs/conf-server/noahService'


class CheckCurrentInstanceTypeModularInput(SplunkARModularInput):
    """Modular input to determine and save current instance type to app config"""
    title = 'Edge Check Current Instance Type Modular Input'
    description = 'Determine the environment the app is installed'
    app = constants.APP_NAME
    name = 'splunkedge_check_current_instance_type_modular_input'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def run(self) -> None:
        current_instance, current_spacebridge = self.get_current_instance_and_spacebridge_server()

        if current_instance is not None and current_spacebridge is not None:
            config.update_app_config(
                auth_header=self.session_key,
                current_instance_type=current_instance,
                spacebridge_hostname=current_spacebridge
            )
            self.logger.debug('Updated the app config with current instance type and current spacebridge information')
        elif current_instance is not None:
            config.update_app_config(
                auth_header=self.session_key,
                current_instance_type=current_instance
            )
            self.logger.debug('Updated the app config with current instance type information')
        elif current_spacebridge is not None:
            config.update_app_config(
                auth_header=self.session_key,
                spacebridge_hostname=current_spacebridge
            )
            self.logger.debug('Updated the app config with current spacebridge information')

        else:
            self.logger.debug(
                f"Could not update the app config with current instance type information, current_instance={current_instance}, current_spacebridge={current_spacebridge}")

    def get_current_instance_and_spacebridge_server(self) -> Tuple[Optional[InstanceType], Optional[str]]:
        default_spacebridge_server = None
        current_instance_type = None
        current_spacebridge_server = default_spacebridge_server

        try:
            current_spacebridge_server, is_cloud_instance = general_requests.get_spacebridge_endpoint(self.session_key)
            if is_cloud_instance is not None:
                if is_cloud_instance:
                    current_instance_type = InstanceType.CLOUD_NOAH
                    response = splunkd_requests.get(path=NOAH_SERVICE_ENDPOINT_PATH, auth_header=self.session_key)

                    if response.status_code != HTTPStatus.OK:
                        current_instance_type = InstanceType.CLOUD_CLASSIC
                else:
                    current_instance_type = InstanceType.ON_PREM

            return current_instance_type, current_spacebridge_server
        except httplib.HTTPException:
            self.logger.error(f"Deployment information cannot be retrieved, status code={response.status_code}")
            return current_instance_type, current_spacebridge_server
        except Exception as e:
            self.logger.error(f"Cannot retrieve current spacebridge server information, error={e}")
            return None, None


if __name__ == '__main__':
    m = CheckCurrentInstanceTypeModularInput(LOGGER)
    m.execute()
