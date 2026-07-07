import requests
import os
import json

import splunk.entity as entity
import splunk.admin as admin
import splunk.version as ver

from solnlib import conf_manager
from splunktaucclib.rest_handler.endpoint.validator import Validator
from distutils.version import LooseVersion


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class ValidateAccount(Validator):
    def __init__(self, *args, **kwargs):
        """
        :param validator: user-defined validating function
        """
        super(ValidateAccount, self).__init__()
        self.my_app = __file__.split(os.sep)[-3]

    def get_proxy_settings(self, splunk_session_key):
        """
        This function will return Proxy URI.
        :param splunk_session_key: Splunk session key
        """
        proxy_data = None
        try:
            entities = entity.getEntities(['admin', 'passwords'], namespace=self.my_app, owner='nobody', sessionKey=splunk_session_key, search=self.my_app)
            proxy_file_obj = conf_manager.ConfManager(splunk_session_key, self.my_app, realm='__REST_CREDENTIAL__#' +
                                                      self.my_app+'#configs/conf-ta_ps_flashblade_settings').get_conf("ta_ps_flashblade_settings").get('proxy')
            
            if proxy_file_obj.get('proxy_enabled') == '1':
                proxy_url = proxy_file_obj.get('proxy_url')
                proxy_port = proxy_file_obj.get('proxy_port')
                proxy_http = "http://"+proxy_url+":"+proxy_port

                if proxy_file_obj.get('proxy_username') and proxy_file_obj.get('proxy_password'):
                    for _, value in entities.iteritems():
                        if value['username'].partition('`')[0] == 'proxy' and not value['clear_password'].startswith('`'):
                            cred = json.loads(value.get('clear_password','{}'))
                            proxy_password = cred.get('proxy_password', '')
                            break
                    proxy_username = proxy_file_obj.get('proxy_username')
                    proxy_https = "https://"+proxy_username+":" + \
                        proxy_password+"@"+proxy_url+":"+proxy_port

                proxy_data = {
                    "http": proxy_http,
                    "https": proxy_https
                }
        except conf_manager.ConfManagerException:
            pass
        finally:
            return proxy_data

    def check_api_version(self, header, resp, server_address, verify_ssl, proxy_settings):
        '''
        This checks for the REST API Versions supported by FlashBlade.
        :param header : Header to be passed in Endpoint
        :param resp : response from login endpoint
        :param server_address : ip address of FlashBlade Server
        :param verify_ssl : should verify ssl or not
        :param proxy_settings : settings for proxy server
        :return False if api version less than 1.5, True otherwise
        '''
        del header['api-token']
        header['x-auth-token'] = resp.headers['x-auth-token']
        supported_version_list = requests.get(
            server_address+"/api/api_version", header, verify=verify_ssl, proxies=proxy_settings)
        flashblade_api_version = LooseVersion(str(supported_version_list.json()['versions'][-1]))
        min_support = LooseVersion("1.5")
        if flashblade_api_version < min_support:
            msg = 'Purity FlashBlade version below 2.2.9 is not supported. Please Upgrade to latest Purity Version available'
            self.put_msg(msg)
            return False

        return True

    def validate(self, value, data):
        """
        Check if the given value is valid.
        :param value: value to validate.
        :param data: whole payload in request.
        :return True or False
        """
        # Get Splunk Session Key
        splunk_session_key = GetSessionKey().session_key

        # Get Splunk Version
        splunk_version = ver.__version__

        # Get proxy settings information
        proxy_settings = self.get_proxy_settings(splunk_session_key)

        # Set parameters
        server_address = data['server_address']
        api_token = data['api_token']
        verify_ssl = bool(int(data['verify_ssl']))

        url = server_address+"/api/login"
        header = {
            'api-token': api_token,
            'user-agent': "Splunk/{}".format(splunk_version)
        }

        # Create Connection
        try:
            resp = requests.post(url, headers=header,
                                 verify=verify_ssl, proxies=proxy_settings)
            resp.raise_for_status()
            return self.check_api_version(header, resp, server_address, verify_ssl, proxy_settings)
        except Exception as e:
            if 'resp' in locals() and resp.status_code == 401:
                msg = "Invalid API Token. Please enter valid API Token"
            else:
                msg = "Please enter valid Server Address, configure valid proxy settings or verify SSL certificate."

            self.put_msg(msg)
            return False
