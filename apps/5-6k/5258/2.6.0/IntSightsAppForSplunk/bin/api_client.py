import ta_intsights_declare     # noqa: F401
import requests
import uuid
import json
import os
import time

from six.moves import urllib
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from log_manager import setup_logging
import constants as const
from intsights_utils import (
    get_proxy_info,
    get_credentials,
)
from errors import (
    APIError,
    QuotaExceededError,
    InvestigationForbiddenError,
    InvestigationFailedError,
    InvestigationDisabledError,
    ConfigurationError,
    InvalidAPICredentialsError,
)

STATUS_FORCELIST = list(range(500, 600)) + [429, ]
REQUEST_TIMEOUT = 120       # in seconds
POST_TAG_COMMENT_REQUEST_TIMEOUT = 180    # in seconds
REQUEST_POLL_TIME = 3       # in seconds
ACCOUNT_STANZA_NAME = "account"
COMMON_URL = 'public/v1/apps/splunk'
COMMON_V2_URL = 'public/v2/app/splunk'
ENDPOINTS = {
    'tags': 'iocs/tags/batch',
    'comments': 'iocs/comments/batch',
    'investigate': 'iocs/investigate',
    'whitelist': '/iocs/whitelist',
}

logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0])


class APIClient(object):
    """A Client for all IntSights API related transactions."""

    def __init__(self, session_key, mod_logger=None):
        """Initialize an object."""
        self.logger = mod_logger or logger
        self.session_key = session_key
        self.sync_id = str(uuid.uuid4())

        self.account = get_credentials(ACCOUNT_STANZA_NAME, session_key)
        self.validate_account(self.account)
        self.domain = self.account.get('server_address')
        self.base_url = 'https://{}/{}'.format(self.domain.strip('/'), COMMON_URL)
        self.base_v2_url = 'https://{}/{}'.format(self.domain.strip('/'), COMMON_V2_URL)

        self.session = self.get_requests_retry_session()
        self.session.verify = const.VERIFY_SSL
        self.session.proxies = get_proxy_info(session_key)
        self.session.auth = (self.account.get('account_id'), self.account.get('api_key'))
        self.session.headers.update = {
            "Content-type": "application/json",
            "Accept": "application/json",
        }

    @classmethod
    def validate_account(cls, account):
        """Validate the given account."""
        if not (isinstance(account, dict) and account.get('server_address')
                and account.get('account_id') and account.get('api_key')):
            err_msg = (
                'Could not retrieve API Credentials.'
                ' Please recheck that API Credentials are configured properly.'
            )
            raise ConfigurationError(message=err_msg, reason=err_msg)
        return True

    def get_requests_retry_session(
        self,
        retries=3,
        backoff_factor=60,
        status_forcelist=STATUS_FORCELIST,
        method_whitelist=["GET", "POST", "HEAD"]
    ):
        """
        Create and return a session object with retry mechanism.

        :param retries: Maximum number of retries to attempt
        :param backoff_factor: Backoff factor used to calculate time between retries. e.g. For 10 - 5, 10, 20, 40,...
        :param status_forcelist: A tuple containing the response status codes that should trigger a retry.
        :param method_whiltelist: HTTP methods on which retry will be performed.

        :return: Session Object
        """
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            method_whitelist=method_whitelist
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    # Decorator
    def handle_common_errors(method):
        """Handle common errors in API response."""
        def wrapper(self, *args, **kwargs):
            err = None
            err_msg = None
            try:
                res = method(self, *args, **kwargs)

                if res is None:
                    raise APIError('APIError: Did not receive response from API.', response=res)

                if res.status_code == 401:
                    raise InvalidAPICredentialsError(response=res)

                return res

            except requests.exceptions.Timeout as ex:
                err_msg = 'TimeoutError: Timeout while requesting data from IntSights Platform.'
                err = ex

            except requests.exceptions.SSLError as ex:
                err_msg = 'SSLError: Please verify the SSL certificate for the provided configuration.'
                err = ex

            except requests.exceptions.ProxyError as ex:
                err_msg = 'ProxyError: Invalid Proxy credentials. Please recheck your Proxy settings.'
                err = ex

            except requests.exceptions.ConnectionError as ex:
                err_msg = 'ConnectionError: Error while connecting to IntSights Platform.'
                err = ex

            except requests.exceptions.RequestException as ex:
                err_msg = 'RequestError: Error while fetching data from IntSights Platform.'
                err = ex

            raise APIError(err_msg, err)

        return wrapper

    # Decorator
    def handle_get_errors(method):
        """Handle errors in API response."""
        def wrapper(self, *args, **kwargs):
            res = method(self, *args, **kwargs)

            if res is None:
                raise APIError('APIError: Did not receive response from API.', response=res)

            res_json = None
            try:
                res_json = res.json()
            except Exception:
                pass

            if isinstance(res_json, dict):
                if 'error' in res_json:
                    err = res_json['error'].get('name')
                    if err == 'Investigation failed':
                        raise InvestigationFailedError(res_json['error'].get('message'), response=res)
                    elif err == 'Investigation forbidden' == err:
                        raise InvestigationForbiddenError(response=res)
                    elif err == 'Investigation':
                        raise InvestigationDisabledError(response=res)
                    elif err == 'quota exceeded':
                        raise QuotaExceededError(response=res)
                    else:
                        raise APIError(reason='Received unknown API error for {} -- {}'.format(
                            res.url, json.dumps(res_json['error'], ensure_ascii=False)), response=res)
                else:
                    return res_json

            res.raise_for_status()
            raise APIError(reason='URL: {} | Status code: {} | Response: {}'.format(
                res.url, res.status_code, res.text), response=res)

        return wrapper

    # Decorator
    def handle_post_errors(method):
        """Handle errors in API response."""
        def wrapper(self, *args, **kwargs):
            res = method(self, *args, **kwargs)

            if res is None:
                raise APIError('APIError: Did not receive response from API.', response=res)

            if res.status_code in (200, 201):
                return res

            res.raise_for_status()
            raise APIError(reason='URL: {} | Status code: {} | Response: {}'.format(
                res.url, res.status_code, res.text), response=res)

        return wrapper

    def build_url(self, endpoint, *objects):
        """Build full url."""
        objects = [urllib.parse.quote_plus(arg, safe="") for arg in objects]
        if 'whitelist' in endpoint:
            return '{}/{}/{}'.format(
                self.base_v2_url,
                endpoint.strip('/'),
                '/'.join(objects),
            ).rstrip('/')
        else:
            return '{}/{}/{}'.format(
                self.base_url,
                endpoint.strip('/'),
                '/'.join(objects),
            ).rstrip('/')

    @handle_post_errors
    @handle_common_errors
    def post_comments(self, comments):
        """Post given comments."""
        url = self.build_url(ENDPOINTS['comments'])
        params = {'syncId': self.sync_id}

        return self.session.post(url, params=params, json=comments, timeout=POST_TAG_COMMENT_REQUEST_TIMEOUT)

    @handle_post_errors
    @handle_common_errors
    def post_tags(self, tags):
        """Post given tags."""
        url = self.build_url(ENDPOINTS['tags'])
        params = {'syncId': self.sync_id}

        return self.session.post(url, params=params, json=tags, timeout=POST_TAG_COMMENT_REQUEST_TIMEOUT)

    @handle_get_errors
    @handle_common_errors
    def get_ioc_investigation(self, ioc_value):
        """Get investigation data on given IOC value."""
        url = self.build_url(ENDPOINTS['investigate'], ioc_value)
        params = {'syncId': self.sync_id}

        # Handle Async Job Request
        res = True
        while res:
            res = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            res_json = None
            try:
                res_json = res.json()
            except Exception:
                break
            if res_json and ('content' in res_json) and \
               ('status' in res_json['content']) and ('type' not in res_json['content']):
                self.logger.info('Investigate API request status: "{}".'.format(res_json['content']['status']))
                self.logger.info('Check status again in {} seconds.'.format(REQUEST_POLL_TIME))
                time.sleep(REQUEST_POLL_TIME)
                continue
            break

        return res

    @handle_common_errors
    def get_deleted_whitelist(self, created_date, next_offset):
        """Get the whitelisted data."""
        url = self.build_url(ENDPOINTS['whitelist'])
        params = {'whitelisted': 'true'}
        if created_date:
            params.update({'updatedAfter': created_date})
        if next_offset:
            params.update({'offset': next_offset})

        return self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)

    # Decorator
    def handle_input_response_errors(method):
        """Handle errors from input response."""
        def wrapper(self, *args, **kwargs):
            res = method(self, *args, **kwargs)
            if res is None:
                raise Exception('Did not receive response from API.')
            if res.status_code != 200:
                if res.status_code == 429:
                    raise Exception(
                        "API limit has been reached for collecting the {}.... "
                        "Please try after some time".format(kwargs.get('input_type')))
                else:
                    raise Exception(
                        "Not able to make successful API call to collect "
                        "{} : Response code : {}".format(kwargs.get('input_type'), res.status_code))

            return res

        return wrapper

    @handle_input_response_errors
    @handle_common_errors
    def get_input_response(self, endpoint, params, input_type=None):
        """Get response for inputs."""
        if input_type == "iocs":
            url = 'https://{}/{}/{}'.format(self.domain.strip('/'), COMMON_V2_URL, endpoint.strip('/'))
        else:
            url = self.build_url(endpoint)

        return self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
