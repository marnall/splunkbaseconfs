import ipaddress
import socket
import requests
from requests.exceptions import ConnectionError
from http import HTTPStatus

from constants import (
    SSE_API_URL,
    SSE_CONNECTOR_CONTEXT_BODY,
    DEFAULT_SSE_CONNECTOR_PORT,
    DEFAULT_SPLUNK_API_PORT,
    SPLUNK_API_URI_TEMPLATE,
    SSE_FQDN_DEFAULT_DOMAIN,
    DEFAULT_SPLUNK_HOST
)
from utils import get_splunk_guid
from errors import ApiClientError, ConnectorNotFound


class BaseApiClient:

    _request = requests

    def _get(self, *args, **kwargs):
        return self.__perform('GET', *args, **kwargs)

    def _post(self, *args, **kwargs):
        return self.__perform('POST', *args, **kwargs)

    def _put(self, *args, **kwargs):
        return self.__perform('PUT', *args, **kwargs)

    def _patch(self, *args, **kwargs):
        return self.__perform('PATCH', *args, **kwargs)

    def _delete(self, *args, **kwargs):
        return self.__perform('DELETE', *args, **kwargs)

    def __perform(self, method, *args, **kwargs):

        try:
            response = self._request.request(method, *args, **kwargs)
            return response
        except ConnectionError:
            raise ConnectorNotFound

    @staticmethod
    def url_for(url, endpoint):
        return f'{url}/{endpoint}'

    @staticmethod
    def check_response_status(response):
        if not response.ok and response.status_code != HTTPStatus.CONFLICT:
            raise ApiClientError(
                response.status_code,
                response.text
            )


class ConnectorApiClient(BaseApiClient):

    base_url = SSE_API_URL
    api_version = 'v1'

    def __init__(self, port=DEFAULT_SSE_CONNECTOR_PORT,
                 splunk_api_port=DEFAULT_SPLUNK_API_PORT,
                 splunk_host=DEFAULT_SPLUNK_HOST,
                 sse_domain=SSE_FQDN_DEFAULT_DOMAIN):
        self.url = self.base_url.format(port=port, version=self.api_version)
        self.sse_domain = sse_domain
        self.splunk_api_port = splunk_api_port
        self.splunk_host = splunk_host

    def _get_context_payload(self):
        context = SSE_CONNECTOR_CONTEXT_BODY
        if self.splunk_api_port != DEFAULT_SPLUNK_API_PORT:
            context['settings']['client']['administration']['uri'] = \
                SPLUNK_API_URI_TEMPLATE.format(port=self.splunk_api_port)
        if self.sse_domain != SSE_FQDN_DEFAULT_DOMAIN:
            context['settings']['exchange']['fqdn'] = self.sse_domain
        if self.splunk_host != DEFAULT_SPLUNK_HOST:
            if not self._is_ip(self.splunk_host):
                context['clientInfo']['ip'] = socket.gethostbyname(
                    self.splunk_host)
            else:
                context['clientInfo']['ip'] = self.splunk_host
        if not context['clientInfo']['guid']:
            context['clientInfo']['guid'] = get_splunk_guid()
        return context

    @staticmethod
    def _is_ip(var):
        try:
            ipaddress.ip_address(var)
        except ValueError:
            return False
        else:
            return True

    def check_connection(self):
        try:
            response = self._get(self.url_for(self.url, 'contexts'))
            if response.ok:
                return True
            else:
                self.check_response_status(response)
        except ConnectorNotFound:
            return False

    def create_context(self):
        response = self._post(
            self.url_for(self.url, 'contexts/'),
            json=self._get_context_payload()
        )
        self.check_response_status(response)

    def remove_context(self):
        response = self._delete(
            self.url_for(self.url, 'contexts/default'),
        )
        self.check_response_status(response)

    def activate(self, token):
        response = self._post(
            self.url_for(self.url, 'contexts/default/activations'),
            json={
                'token': token
            }
        )
        self.check_response_status(response)

    def shutdown(self):
        response = self._post(
            self.url_for(self.url, 'action'),
            params={'type': 'shutdown'}
        )
        self.check_response_status(response)

    def reset(self):
        response = self._post(
            self.url_for(self.url, 'action'),
            params={'type': 'reset'}
        )
        self.check_response_status(response)
