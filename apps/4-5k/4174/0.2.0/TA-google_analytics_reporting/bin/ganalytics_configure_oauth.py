""" Custom endpoint to configure OAuth. Adapted from pas_ref_app. """

import os
import json
import logging
import logging.handlers
import sys
import splunk.rest  # pylint: disable=import-error
import splunk.util  # pylint: disable=import-error
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path  # pylint: disable=import-error
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
OAUTH_SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
# set our path to this particular application directory (which is suppose to be <appname>/bin)
app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(app_dir)


def setup_logger():
    """ Sets up logger """
    logger = logging.getLogger('ganalytics_configure_oauth')
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(
        make_splunkhome_path(['var', 'log', 'splunk', 'ganalytics_configure_oauth.log']),
        maxBytes=25000000, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger


endpoint_logger = setup_logger()


class oauth_exchange(splunk.rest.BaseRestHandler):  # pylint: disable=too-few-public-methods
    """ OAuth exchange endpoint. Given client ID/secret, retrieves and stores a refresh token. """
    def handle_POST(self):
        """ Handle POST request """
        try:
            client_id = self.args.get('client_id')
            client_secret = self.args.get('client_secret')
            auth_code = self.args.get('auth_code')
            input_name = self.args.get('input_name')

            storage = Storage(os.path.join(app_dir, input_name + '_google_analytics_creds'))

            flow = OAuth2WebServerFlow(client_id, client_secret, OAUTH_SCOPE, REDIRECT_URI)
            credentials = flow.step2_exchange(auth_code)
            endpoint_logger.debug("Obtained OAuth2 credentials!")
            storage.put(credentials)

            # Update view ID XML
            splunk.rest.simpleRequest(
                '/servicesNS/nobody/TA-google_analytics_reporting/saved/searches/'
                'Google%20Analytics%20Reporting%20-%20Update%20View%20IDs/dispatch',
                method='POST', sessionKey=self.sessionKey)

        except Exception, e:  # pylint: disable=broad-except
            endpoint_logger.exception(e)
            self.response.setStatus(500)
            self.response.write(str(e))


class oauth_status(splunk.rest.BaseRestHandler):  # pylint: disable=too-few-public-methods
    """ OAuth status endpoint. Returns if OAuth is configured or not. """
    def handle_GET(self):
        """ Handle GET request """
        try:
            input_name = self.args.get('input_name')
            is_configured = os.path.isfile(os.path.join(app_dir, input_name +
                                                        '_google_analytics_creds'))
            endpoint_logger.debug("Is Google Analytics TA Configured: %s", str(is_configured))

            state = json.dumps({
                "configured": is_configured
            })
            self.response.write(state)
        except Exception, e:  # pylint: disable=broad-except
            endpoint_logger.exception(e)
            self.response.setStatus(500)
            self.response.write(str(e))
