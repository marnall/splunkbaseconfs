import traceback
import requests
import json
from requests.auth import HTTPBasicAuth
from ecs_util import create_proxy_uri_dict
import time
requests.packages.urllib3.disable_warnings()


class ECSConnect(object):
    """Initialize ECSConnect objects which aims to build a basic structure of url and handle token and api calls."""

    def __init__(self, ip_address, PORT, username, password, end_time, helper, verify_ssl, protocol='https'):
        """
        Initialize ESConnect object.

        :param ip_address: Ip address of ECS simulator
        :param PORT: Port of ECS simulator
        :param username: Username of ECS simulator
        :param password: password of ECS simulator
        :param end_time: end time in Api call
        :param verify_ssl: SSL verification
        :param helper: splunk helper object
        :param protocal: protocol
        """
        self.ip_address = ip_address
        self.port = PORT
        self.username = username
        self.password = password
        self.base_url = '{protocol}://{ip_address}:{port}/{{endpoint}}'.format(
            protocol=protocol, ip_address=ip_address, port=PORT)
        self._reset_session()
        self.end_time = end_time
        self.helper = helper
        self.verify_ssl = verify_ssl
        self.account = self.helper.get_arg("global_account")
        self.proxies = create_proxy_uri_dict(self.account)
        self.STATUS_FORCELIST = list(range(500, 600)) + [429, ]
        self.SUCCESSFUL_STATUSCODE = list(range(200, 299))
        self.TIMEOUT = 15

    def _reset_session(self):
        """Reset current session."""
        self.session = requests.Session()

    def _build_url(self, endpoint):
        """
        Build URL.

        :param endpoint: rest endpoint
        :return: rest endpoint url
        """
        return self.base_url.format(endpoint=endpoint.lstrip('/'))

    def choose_api_call(self, url, headers, auth, querystring, method):
        """
        Function will choose which api call should be made.

        :param url: rest endpoint url
        :param headers: headers for rest api
        :param auth: True or False(True: auth call will be made, False: other rest endpoint call will be made)
        :param querystring: parameters for rest api call
        :return: api response
        """
        response = None
        if auth:
            try:
                response = self.session.get(url,
                                            headers=headers,
                                            verify=self.verify_ssl,
                                            auth=HTTPBasicAuth(self.username, self.password),
                                            proxies=self.proxies,
                                            timeout=self.TIMEOUT)
            except APIError as e:
                self.helper.log_error(
                    "API Error occured for Endpoint: {} : Message: {}".format(str(url), str(e)))
            try:
                if response.status_code == 401:
                    self.helper.log_error(
                        "Authentication Error for Endpoint: {} : Message: Cannot able to access token".format(url))
                    exit()
            except Exception as e:
                self.helper.log_error(
                    "API Error occured for Endpoint: {} : Message: {}".format(url, e))
                exit()
        elif method == "POST":
            headers = self.session.headers
            if "flux" in url:
                headers["Content-Type"] = "application/json"
                headers["X-Fluxd-Disable-Range-Validation"] = "true"
                headers["X-Fluxd-Disable-Op-Validation"] = "true"
            try:
                response = self.session.post(url,
                                             headers=headers,
                                             data=querystring,
                                             verify=self.verify_ssl,
                                             proxies=self.proxies,
                                             timeout=self.TIMEOUT)
            except APIError as e:
                self.helper.log_error(
                    "API error Ocuured for Endpoint: {} : Message: {}".format(url, str(e)))
        else:
            try:
                response = self.session.get(url,
                                            headers=self.session.headers,
                                            params=querystring,
                                            verify=self.verify_ssl,
                                            proxies=self.proxies,
                                            timeout=self.TIMEOUT)
            except APIError as e:
                self.helper.log_error(
                    "API error Ocuured for Endpoint: {} : Message: {}".format(url, str(e)))
        return response

    def get_endpoint_response(self, endpoint, querystring={}, retry_login=1, auth=False, headers={}, method=None):
        """
        GET call to endpoint.

        :param endpoint: rest endpoint
        :param params: parameters to send
        :param retry_login: number of retries if token expires
        :return: response
        """
        url = self._build_url(endpoint)
        response = None
        retry_login = retry_login if isinstance(retry_login, int) else 0
        count = 0
        self.helper.log_debug("API Endpoint : {}".format(url))
        while True:
            r = self.choose_api_call(url, headers, auth, querystring, method)
            try:
                response = self._check_response(r, url)
                status_code = int(response.status_code)
                if status_code == 401 or status_code in self.STATUS_FORCELIST:
                    if count < retry_login:
                        # for more API calls, the server returns status_code: 503 (Server Error: Service Temporarily Unavailable)  # noqa:E501
                        if status_code == 429 or ("flux" in url and status_code == 503):
                            time.sleep(5)
                        else:
                            self.renew_token()
                        count += 1
                        continue
                    else:
                        response.raise_for_status()
            except APIError as e:
                err_message = "API Endpoint: {} with Payload: {} has following error occured :{} Traceback: {}".format(
                    url, querystring, str(e), traceback.format_exc())
                self.helper.log_error("{}".format(err_message))
                break
            except Exception as e:
                err_message = "API Endpoint: {} with Payload: {} has following error occured :{} Traceback: {}".format(
                    url, querystring, str(e), traceback.format_exc())
                self.helper.log_error("{}".format(err_message))
                break
            break
        return response

    def handle_token(self, helper, checkpoint_token):
        """
        Handle token mechanism.

        :param checkpoint_token: retrive from checkpoint
        """
        token = helper.get_check_point(checkpoint_token)
        if token:

            headers = {
                'Accept': "application/json",
                'X-SDS-AUTH-TOKEN': str(token),
            }
            self.session.headers.update(headers)
        else:
            self.renew_token()

    def create_token(self, username, password):
        """
        Create a new token.

        :param username: username of ecs account
        :param password: password of ecs account
        :return: api response from login endpoint
        """
        endpoint = 'login'
        headers = {'Accept': 'application/json'}
        return self.get_endpoint_response(endpoint, auth=True, headers=headers)

    def renew_token(self):
        """In case token expire then renew a token."""
        self._reset_session()
        token = self.create_token(self.username, self.password)
        token_name = "x-sds-auth-token:{}".format(self.ip_address)
        token = str(token.headers["X-SDS-AUTH-TOKEN"])
        self._set_token(token, token_name)

    def _set_token(self, token, token_name):
        """
        Set token in header.

        :param token: authentication token
        """
        self.TOKEN = token
        headers = {
            'Accept': "application/json",
            'X-SDS-AUTH-TOKEN': self.TOKEN,
        }
        self.helper.save_check_point(token_name, self.TOKEN)
        self.session.headers.update(headers)

    def _check_response(self, response, url):
        """
        Check returned response of rest endpoint.

        :param response: response from rest endpoint
        :return: response
        """
        status_code = int(response.status_code)

        # For error code where response is empty, header is not coming eg: code: 404
        if response.headers.get('Content-Type') == 'text/html':
            raise APIError(status_code, 'Not Found', 'Unable to find entity in request URL')
        else:
            # Flux is returning 500 status_code when token is expired
            if not (status_code in self.SUCCESSFUL_STATUSCODE or status_code == 401 or ("flux" in url and status_code in self.STATUS_FORCELIST)):  # noqa:E501
                try:
                    data = json.loads(response.text)
                    code = data.get('code', 'Unknown Error...')
                    description = data.get('description', 'Unknown Error...')
                except Exception:
                    code = status_code
                    description = response.text
                raise APIError(status_code, code, description)

        return response


class APIError(Exception):
    """Handle Api related error."""

    def __init__(self, http_status_code, error_code, error_msg):
        """
        Initialize APIError object.

        :param http_status: rest api status code
        :param error_code: rest api error code
        :pararm error_msg: rest api error description
        """
        self.http_status_code = str(http_status_code)
        self.error_code = str(error_code)
        self.error_msg = str(error_msg)

    def __str__(self):
        """Send error message to Splunk UI."""
        msg = 'http_status_code[{}], error code[{}], Message: {}'.format(
            self.http_status_code, self.error_code, self.error_msg)
        return str(msg)
