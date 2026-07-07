import os
import sophos_consts
import sophos_common_utils as utils

from solnlib.utils import is_true
from log_manager import setup_logging
from splunk_aoblib.rest_helper import TARestHelper


_LOGGER = setup_logging("sophos_mod_input")


class SophosCollect(object):
    """A class to establish connection with Sophos and get data using REST API."""

    def __init__(self, session_key):
        """Intialize SophosCollect object to get data from sophos platform.

        Args:
            session_key (object): Splunk session key
        """
        self.SESSION_KEY = session_key
        self.APP_NAME = __file__.split(os.sep)[-3]

        try:
            self.PROXY_URI = utils.get_proxy_uri(self.APP_NAME, self.SESSION_KEY)
            self.SOPHOS_CONFIGS = utils.get_sophos_configs()
        except Exception as e:
            _LOGGER.error(
                "Unexpected error occured while initializing SophosCollect: {}".format(e)
            )
            exit()

        if self.PROXY_URI:
            _LOGGER.info("Proxy is enabled on the instance.")

        self.VERIFY_SSL = is_true(self.SOPHOS_CONFIGS.get("verify_cert", "true"))

    @staticmethod
    def request_sophos_access_token(
        sophos_auth_url,
        sophos_client_id,
        sophos_client_secret,
        sophos_verify_cert,
        proxy_uri
    ):
        """Generate new access token with Sophos credentials.

        Args:
            sophos_auth_url (str): Sophos base Auth URL
            sophos_client_id (str): Sophos Client ID
            sophos_client_secret (str): Sophos Client Secret
            sophos_verify_cert (bool): SSL certificate validation flag
            proxy_uri (str): Proxy URI

        Returns:
            object: requests.Response object
        """
        payload = 'grant_type=client_credentials&client_id={}&client_secret={}&scope=token'.format(
            str(sophos_client_id),
            str(sophos_client_secret)
        )
        headers = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": sophos_consts.USER_AGENT}

        request_url = "{scheme}{url}{endpoint}".format(
            scheme="https://", url=sophos_auth_url, endpoint=sophos_consts.AUTH_ENDPOINT
        )
        response = TARestHelper().send_http_request(
            request_url, "post", payload=payload, verify=sophos_verify_cert, proxy_uri=proxy_uri, headers=headers
        )
        return response

    def get_and_update_access_token(self):
        """Get new access token and store it in passwords.conf.

        Returns:
            str: sophos access token
        """
        _LOGGER.info("Sophos access token expired. Fetching new access token.")

        try:
            sophos_client_id = self.SOPHOS_CONFIGS.get("client_id", "")
            sophos_client_secret, _ = utils.get_sophos_clear_tokens(self.APP_NAME, self.SESSION_KEY)

            response = self.request_sophos_access_token(
                sophos_consts.AUTH_BASE_URL, sophos_client_id, sophos_client_secret, self.VERIFY_SSL, self.PROXY_URI
            )
            if response.ok:
                access_token = response.json()["access_token"]
                utils.save_sophos_credentials(self.APP_NAME, self.SESSION_KEY, access_token)
                _LOGGER.info("Access token generated and updated.")
            else:
                reason = self.get_error_message(response)
                _LOGGER.error(
                    "Some error occured while regenerating the Access token: Status Code: {},Reason: {}."
                    " Exiting the data collection".format(
                        response.status_code, reason
                    )
                )
            return None
        except Exception as e:
            _LOGGER.error(
                "Unexpected error occured while generating or saving new token: {}".format(e)
            )

    def _call_endpoint(
        self,
        sophos_url,
        endpoint,
        parameters={},
        payload={},
        method="post",
        headers={},
        scheme_flag=False,
    ):
        """Make REST call to the provided Sophos endpoints.

        Args:
            sophos_url (str): Sophos base URL
            endpoint (str): Sophos endpoint
            parameters (dict): Request parameters
            payload (str): Request body
            method (str): HTTP method
            headers (dict): Request headers

        Returns:
            object: requests.Response object
        """

        if not scheme_flag:
            request_url = "{scheme}{url}{endpoint}".format(
                scheme="https://", url=sophos_url, endpoint=endpoint
            )
        else:
            request_url = "{url}{endpoint}".format(
                url=sophos_url, endpoint=endpoint
            )

        _LOGGER.debug("Executing REST call: {}".format(request_url))

        retry = 0
        while retry <= sophos_consts.GLOBAL_RETRY:
            try:
                # Get stored access token
                secret_key, access_token = utils.get_sophos_clear_tokens(
                    self.APP_NAME, self.SESSION_KEY
                )
                headers["Authorization"] = "Bearer {}".format(access_token)
                headers["User-Agent"] = sophos_consts.USER_AGENT

                if not request_url.startswith("https"):
                    break

                # Execute actual API call
                response = TARestHelper().send_http_request(
                    request_url,
                    method,
                    headers=headers,
                    parameters=parameters,
                    verify=self.VERIFY_SSL,
                    proxy_uri=self.PROXY_URI,
                    payload=payload,
                    timeout=(sophos_consts.CONNECT_TIMEOUT, sophos_consts.READ_TIMEOUT),
                )

                # Parse response from API
                if response.ok:
                    _LOGGER.info("Successfully obtained response from: {}".format(request_url))
                    return response
                if response.status_code == 401:
                    self.get_and_update_access_token()
                elif response.status_code == 400:
                    reason = self.get_error_message(response)
                    if reason:
                        _LOGGER.error(reason)
                    else:
                        message = "Bad Request, Check URL/Endpoint."
                        _LOGGER.error(message)
                    break
                elif response.status_code == 403:
                    message = "Forbidden. Not having permission to perform this action."
                    _LOGGER.error(message)
                    break
                elif response.status_code == 429:
                    message = "Too many Requests."
                    _LOGGER.error(message)
                    break
                elif response.status_code >= 500:
                    message = "Internal Server error."
                    _LOGGER.error(message)
                    break
                else:
                    reason = self.get_error_message(response)
                    message = "Failed to collect data from Sophos! "\
                              "URL:{} Payload: {} Status Code: {}, Reason: {}".format(
                                  request_url, payload, response.status_code, reason
                              )
                    _LOGGER.error(message)
                    break
                retry += 1
            except Exception as e:
                _LOGGER.error(
                    "Unexpected Error while calling {} endpoint. Exception: {}".format(request_url, str(e))
                )
                break
        return None

    def check_credentials(self):
        """
        Check the configuration is done before creating inputs.

        raise ValueError: When configuration is not completed.
        """
        # get sophos_client_id and sophos_client_secret from conf
        sophos_client_id = self.SOPHOS_CONFIGS.get("client_id", "")
        sophos_client_secret = self.SOPHOS_CONFIGS.get("client_secret", "")

        # if any of them are None then the account is not configured
        if not all([sophos_client_id, sophos_client_secret]):
            message = "Sophos credentials are not configured."
            raise ValueError(message)

    @staticmethod
    def get_error_message(response):
        """Return error reason from response.

        Args:
            response(Response Object): Response from sophos Rest endpoint.
        Returns:
            str: error message from response.
        """
        if "errorCode" in response.json():
            return response.json().get("errorCode")
        elif "message" in response.json():
            return response.json().get("message")
        else:
            return response.reason
