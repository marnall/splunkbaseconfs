import logging
import requests

import requests.packages.urllib3 as urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NetAppConnection(object):
    """This is NetAppConnection class."""

    def __init__(self, address, username, passsword, proxy_settings, verify_ssl=True, **kwargs):
        """Initialize NetAppConnection Object."""
        self.address = address
        self.get_base_url = 'https://{}/devmgr/v2/storage-systems/{{system_id}}/{{endpoint}}'.format(self.address)
        self.post_base_url = 'https://{}/devmgr/v2/storage-systems'.format(self.address)
        self.webproxy_url = 'https://{}/devmgr/v2/{{endpoint}}'.format(self.address)
        self.proxy_settings = proxy_settings
        self.verify_ssl = verify_ssl
        self.auth = (username, passsword)
        self.log = logging.getLogger()
        self.__setupSession()

    def __setupSession(self):
        """To setup session."""
        self.log.info('NetApp ESeries: Setting up session.')
        self.conn = requests.Session()
        self.conn.auth = self.auth
        self.conn.verify = self.verify_ssl
        self.log.info('NetApp ESeries: Setting requests ssl verify to: {}'.format(self.verify_ssl))
        self.conn.proxies.update(self.proxy_settings)
        headers = {
            'Content-Type': 'application/json'
        }
        self.conn.headers.update(headers)

    def __checkResponse(self, response):
        """
        Check response from rest endpoint.

        :param response: response from rest endpoint
        :return:response in json format
        """
        if response.ok:
            self.log.info('NetApp ESeries: response OK http_status code: {}'.format(response.status_code))
            return response.json()
        else:
            msg = 'http_status_code: {}'.format(response.status_code)
            try:
                msg = response.json()['errorMessage']
                return None
            except Exception:
                msg = response.text
            finally:
                self.log.error("NetApp Error: response: {}".format(msg))

    def getEndpoint(self, system_id, endpoint, params=None):
        """
        Get request to rest endpoint.

        :param system_id: System ID for the Storage Array
        :param endpoint: endpoint to request
        :param params:parameters to send with request
        :return:response from requested url
        """
        url = self.get_base_url.format(system_id=system_id, endpoint=endpoint)
        self.log.debug('NetApp ESeries debug: GET URL: {}'.format(url))
        self.log.debug('NetApp ESeries debug: GET PARMS: {}'.format(params))
        res = self.conn.get(url, params=params, proxies=self.proxy_settings)
        return self.__checkResponse(res)

    def postEndpoint(self, data=None):
        """
        Post request to rest endpoint.

        :param data: data to send with request
        :return: response from request url
        """
        url = self.post_base_url
        res = self.conn.post(url, data=data, proxies=self.proxy_settings)
        return self.__checkResponse(res)

    def checkSystemId(self, params=None):
        """
        Get request to rest endpoint.

        :param params:parameters to send with request
        :return:response from requested url
        """
        url = self.post_base_url
        res = self.conn.get(url, params=params, proxies=self.proxy_settings)
        return self.__checkResponse(res)

    def getFolderData(self, endpoint, params=None):
        """
        Get request to rest endpoint.

        :param endpoint: endpoint to request
        :param params:parameters to send with request
        :return:response from requested url
        """
        url = self.webproxy_url.format(endpoint=endpoint)
        self.log.debug('NetApp ESeries debug: GET URL: {}'.format(url))
        self.log.debug('NetApp ESeries debug: GET PARMS: {}'.format(params))
        res = self.conn.get(url, params=params, proxies=self.proxy_settings)
        return self.__checkResponse(res)
