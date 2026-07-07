"""
(C) 2020 Splunk Inc. All rights reserved.

Modular Input to register the AR splunkar with SSG.
"""
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

import time

from http import HTTPStatus
from secure_gateway_sdk.services import secure_gateway_service
from splunk import RESTException, rest
from splunkar import constants
from splunkar import logging
from splunkar.util import config
from splunkar.util.modular_input_utils import SplunkARModularInput

sys.path.remove(make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

ATTEMPTS = 5
BACKOFF_INTERVAL_SECONDS = 5
LOGGER = logging.get_logger('init_ssg_app_modular_input')


class RegistrationError(Exception):
    pass


class SplunkARSSGRegistrationModularInput(SplunkARModularInput):
    """
    Modular Input to initialize companion splunkar with Splunk Secure Gateway
    """
    title = 'Splunk App for AR Companion App Registration'
    description = 'Registers Splunk App AR with Splunk Secure Gateway'
    app = constants.APP_NAME
    name = 'splunkar_init_ssg_app_modular_input'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def run(self) -> None:
        for _ in range(ATTEMPTS):
            try:
                version = config.app_version()
                secure_gateway_service.register_companion_app(
                    friendly_name=constants.FRIENDLY_APP_NAME,
                    app_name=constants.APP_NAME,
                    app_id=constants.COMPANION_APP_ID,
                    signature='KojqM0WPQa+EvJuxOlQlUMvkUldfu3MByVwRuyyrwWdC4yUMJfTD9IX6l96wse4I4Us/IhLbZS86Y5krxjJ3Ag==',
                    version=f'{version.major}.{version.minor}.{version.patch}',
                    authtoken=self.session_key,
                    base_url=f'{rest.makeSplunkdUri().rstrip("/")}/services/splunk-app-ar',
                )
                self.logger.info('Registered AR as a companion app with SSG.')
                return

            except RESTException as e:
                if e.statusCode == HTTPStatus.NOT_FOUND:
                    self.logger.exception('SSG is either not installed or the app registration endpoint has moved.')
                    raise e

                self.logger.exception('Failed to register with SSG as a companion app. Retrying...')
                time.sleep(BACKOFF_INTERVAL_SECONDS)

        raise RegistrationError(f'Failed to register AR as a companion app with SSG after {ATTEMPTS} attempts. '
                                f'Please see exception logs for more details.')


if __name__ == '__main__':
    m = SplunkARSSGRegistrationModularInput(LOGGER)
    m.execute()
