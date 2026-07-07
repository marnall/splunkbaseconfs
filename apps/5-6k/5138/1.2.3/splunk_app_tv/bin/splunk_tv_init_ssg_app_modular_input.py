"""
(C) 2020 Splunk Inc. All rights reserved.

Modular Input to initialize companion app
"""
import sys
import os
import splunk
from splunk import rest

from splunk.clilib.bundle_paths import make_splunkhome_path

os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
sys.path.append(make_splunkhome_path(['etc', 'apps', 'splunk_app_tv', 'lib']))

from splunk_tv.util import constants
from splunk_tv.util.logging import get_logger
from secure_gateway_sdk.services.secure_gateway_service import register_companion_app
from secure_gateway_sdk.util.splunk_utils import modular_input_utils
from secure_gateway_sdk.services import kvstore_service as kvstore
from solnlib import modular_input


class InitSSGAppModularInput(modular_input.ModularInput):
    """
    Modular Input to initialize companion app with Splunk Secure Gateway
    """
    title = 'Init SSG App SplunkTV'
    description = 'Initialize the SplunkTV companion app with Splunk Secure Gateway'
    app = 'splunk_app_tv'
    name = 'splunk_tv_init_ssg_app_modular_input'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False
    logger = get_logger(logger_name='splunk_tv_init_ssg_app_modular_input')
    WAIT_TIME_IN_SECONDS = 0.25
    MAX_ERRORS = 5

    def do_run(self, input_config):
        if not modular_input_utils.modular_input_should_run(self.session_key, self.logger):
            self.logger.info("SplunkTV companion app registration will not run")
            return
        self.logger.info('Starting SplunkTV companion app registration')
        try:
            kvstore.wait_until_ready(session_key=self.session_key)
            base_uri = rest.makeSplunkdUri().rstrip("/")
            app_base_url = f'{base_uri}/services/{constants.SPLUNK_TV_APP_NAME}'
            register_companion_app(
                friendly_name=constants.SPLUNK_TV_APP_FRIENDLY_NAME,
                app_id=constants.SPLUNK_TV_APP_ID,
                version=constants.SPLUNK_TV_APP_VERSION,
                app_name=constants.SPLUNK_TV_APP_NAME,
                signature=constants.SPLUNK_TV_APP_SIGNATURE,
                authtoken=self.session_key,
                base_url=app_base_url
            )
        except splunk.RESTException as restException:
            self.logger.exception(f'Failed to connect to Splunk Secure Gateway with exception: {restException}')
            raise restException
        except TimeoutError as timeoutException:
            self.logger.exception(f'Failed to connect to Splunk Secure Gateway with timeout: {timeoutException}')
            raise timeoutException
        except Exception as exception:
            self.logger.exception(f'Failed to connect to Splunk Secure Gateway with unknown exception: {exception}')
            raise exception
        self.logger.info('Successfully connected to Splunk Secure Gateway')


if __name__ == '__main__':
    worker = InitSSGAppModularInput()
    worker.execute()
