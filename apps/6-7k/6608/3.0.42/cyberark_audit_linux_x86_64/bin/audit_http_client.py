from datetime import datetime, timedelta, timezone
from enum import Enum
from http import HTTPStatus
from logging import Logger

import requests
from aws_credentials_provider import AwsCredentialsProvider
from get_audits_response import GetAuditsResponse
from requests.models import Response
from requests_aws4auth.aws4auth import AWS4Auth


class AuditApiQueryParam(Enum):
    APPLICATION_CODES = 'applicationCodes'
    PAGE_SIZE = 'limit'
    CURSOR = 'after'
    START_DATE = 'startDate'


class InternalServerError(Exception):

    def __init__(self, msg, error_code):
        super(InternalServerError, self).__init__(msg)
        self.err_code = error_code


class AuditHttpClient:

    # 'The max number of audits to fetch in each request'
    ALL_SERVICES_FILTER = 'all'

    def __init__(self, credentials_provider: AwsCredentialsProvider, api_endpoint: str, device_name: str, initial_minutes_back_start: int,
                 services_filter: str, page_size: int, logger: Logger, proxy_config=None):
        self._credentials_provider = credentials_provider
        self._api_endpoint = api_endpoint
        self._device_name = device_name
        self._initial_minutes_back_start = initial_minutes_back_start
        self._services_filter = services_filter
        self._page_size = page_size
        self._logger = logger
        self._proxy_config = proxy_config

    @property
    def credentials_provider(self) -> AwsCredentialsProvider:
        return self._credentials_provider

    @property
    def api_endpoint(self) -> str:
        return self._api_endpoint

    @property
    def device_name(self) -> str:
        return self._device_name

    @property
    def initial_minutes_back_start(self) -> int:
        return self._initial_minutes_back_start

    @property
    def services_filter(self) -> str:
        return self._services_filter

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def proxy_config(self):
        return self._proxy_config

    def get_initial_audits_page(self) -> GetAuditsResponse:
        audit_api_url = self._build_get_audits_api_url(api_endpoint=self.api_endpoint, device_name=self.device_name)
        start_time = (datetime.now(timezone.utc) + timedelta(minutes=-self.initial_minutes_back_start)).isoformat()
        params = {AuditApiQueryParam.START_DATE.value: start_time, AuditApiQueryParam.PAGE_SIZE.value: self._page_size}
        self._add_service_filter(params=params, services_filter=self.services_filter)
        self.logger.info(f'Making initial audits API request: start_date={start_time}, page_size={self._page_size}, '
                         f'services_filter={self.services_filter}, '
                         f'proxy_enabled={self._proxy_config is not None}')

        request_kwargs = {'params': params, 'timeout': 30}

        if self._proxy_config:
            request_kwargs['proxies'] = {k: v for k, v in self._proxy_config.items() if k in ('http', 'https')}
            if 'verify' in self._proxy_config:
                request_kwargs['verify'] = self._proxy_config['verify']

        response = self._make_request_with_retry(audit_api_url, request_kwargs)
        return GetAuditsResponse(**response.json())

    def get_next_audits_page(self, next_page_cursor: str) -> GetAuditsResponse:
        audit_api_url = self._build_get_audits_api_url(api_endpoint=self.api_endpoint, device_name=self.device_name)
        params = {AuditApiQueryParam.CURSOR.value: next_page_cursor, AuditApiQueryParam.PAGE_SIZE.value: self._page_size}
        self._add_service_filter(params=params, services_filter=self.services_filter)
        request_kwargs = {'params': params, 'timeout': 30}

        if self._proxy_config:
            request_kwargs['proxies'] = {k: v for k, v in self._proxy_config.items() if k in ('http', 'https')}
            if 'verify' in self._proxy_config:
                request_kwargs['verify'] = self._proxy_config['verify']

        response = self._make_request_with_retry(audit_api_url, request_kwargs)
        self._validate_response(response)
        return GetAuditsResponse(**response.json())

    @staticmethod
    def _build_get_audits_api_url(api_endpoint: str, device_name: str) -> str:
        return f'{api_endpoint}/api/audits/{device_name}'

    def _add_service_filter(self, params: dict, services_filter: str) -> None:
        if services_filter.lower() != self.ALL_SERVICES_FILTER:
            params[AuditApiQueryParam.APPLICATION_CODES.value] = services_filter

    def _execute_request(self, url: str, awsauth: AWS4Auth, kwargs: dict, attempt: str = '') -> Response:
        """Execute a single HTTP GET, mapping request exceptions to InternalServerError."""

        suffix = f' on {attempt}' if attempt else ''
        try:
            return requests.get(url, auth=awsauth, **kwargs)
        except requests.exceptions.ProxyError as e:
            self.logger.error(f'Proxy connection failed{suffix} — check proxy host, port, and credentials. Error: {e}')
            raise InternalServerError(f'Proxy connection failed{suffix}', 502)
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f'Connection failed{suffix} — unable to reach API endpoint. Error: {e}')
            raise InternalServerError(f'Connection to audit API failed{suffix}', 503)
        except requests.exceptions.Timeout as e:
            self.logger.error(f'Request timed out{suffix}. Error: {e}')
            raise InternalServerError(f'Request to audit API timed out{suffix}', 504)
        except requests.exceptions.RequestException as e:
            self.logger.error(f'HTTP request failed{suffix}. Error: {e}')
            raise InternalServerError(f'Audit API request failed{suffix}', 500)

    def _make_request_with_retry(self, url: str, kwargs: dict) -> Response:
        """Make request with automatic retry on auth failure."""

        awsauth: AWS4Auth = self.credentials_provider.get_or_create_aws_credentials()
        self.logger.info('AWS auth credentials obtained successfully')
        response = self._execute_request(url, awsauth, kwargs)
        if response.status_code == HTTPStatus.PROXY_AUTHENTICATION_REQUIRED.value:
            self.logger.error('Proxy authentication failed (407) — the proxy username or password is incorrect')
            raise InternalServerError('Proxy authentication failed', HTTPStatus.PROXY_AUTHENTICATION_REQUIRED.value)
        if response.status_code in (HTTPStatus.UNAUTHORIZED.value, HTTPStatus.FORBIDDEN.value):
            self.logger.warning(f'Auth failed (status={response.status_code}), refreshing credentials and retrying')
            self.credentials_provider.refresh_aws_credentials()
            awsauth = self.credentials_provider.get_or_create_aws_credentials()
            response = self._execute_request(url, awsauth, kwargs, attempt='retry')
        self._validate_response(response)
        return response

    def _validate_response(self, response: Response) -> None:
        """Validate response after retry attempt."""
        if response.status_code != HTTPStatus.OK.value:
            self.logger.error(f'API request failed with status_code={response.status_code}')
            raise InternalServerError('Failure fetching Cyberark Audits', response.status_code)
