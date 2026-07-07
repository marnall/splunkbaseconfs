# Standard library imports
import requests

# Local imports
import logger_manager as log

# Setup logger
logger = log.setup_logging('trustar_modinput')


class TokenAuth(object):
    def __init__(self, **args):
        """ Initialize object of "TokenAuth" class.

        :param args: variable arguments (ex: url, auth_type, session_key, endpoint, etc)
        """

        # Get URL of TruSTAR instance
        self.base_url = args.get('url')
        # Get proxy server information
        self.proxy_server = args.get('proxies')

    def get_access_token(self, api_key, secret_key, verify):
        """ Method that obtains temporary access_token from TruSTAR with the provided credentials.

        :param api_key: API key to be used
        :param secret_key: API secret to be used
        :param verify: true or path to certificate
        :return: response from API call
        """

        # Prepare request body
        body = {'grant_type': 'client_credentials'}
        # Prepare endpoint to hit
        url = self.base_url + '/oauth/token'
        # Prepare request headers
        headers={
            "Client-Type":"API",
            "Client-Version": "1.3",
            "Client-Metatag": "SPLUNK"
        }
        try:
            # Make REST call
            if self.proxy_server:
                response = requests.post(url=url, data=body, auth=(api_key, secret_key), verify=verify,
                                         proxies={"https": self.proxy_server, "http": self.proxy_server},
                                         headers=headers)
            else:
                response = requests.post(url=url, data=body, auth=(api_key, secret_key), verify=verify,
                                         headers=headers)

            # Return response data in json format if HTTP status code is 200
            if response.status_code == 200:
                return response.json()

            # Raise exception if any other HTTP status code is found
            raise Exception(response.text)

        # Handle any exception generated while making REST call
        except Exception, e:
            logger.error(
                "TruSTAR Error: Cannot get access_key for authentication , message %s %s " % (e, e.args))
