import os

from splunktaucclib.rest_handler.endpoint.validator import Validator
from tenable.io import TenableIO as TIO
from tenable_utility import get_proxy_settings, get_app_version

class Utility:
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def get_proxy(self, data):
        return get_proxy_settings(global_account_dict=data)

class TenableIO(Validator):
    def __init__(self, *args, **kwargs):
        """

        :param validator: user-defined validating function
        """
        super(TenableIO, self).__init__()
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
        self.util = Utility()

    def validate(self, value, data):
        try:
            try:
                app_name = self.path.split(
                    '/')[-3] if '/' in self.path else self.path.split('\\')[-3]
                tio = TIO(
                    access_key=data.get("tenable_was_api_key"),
                    secret_key=data.get("tenable_was_secret_key"),
                    url="https://" + data.get("tenable_was_domain").strip('/'),
                    vendor='Tenable',
                    proxies=self.util.get_proxy(data),
                    product='Web Application Scanning',
                    build=get_app_version(app_name)
                )
            except Exception as e:
                msg = "Please enter valid Address, Access key and Secret key {}".format(str(e))
                raise Exception(msg)
            if tio.session.details().get('permissions') < 64:
                msg = 'This integrations requires that the user we connect with is a Tenable.io Administrator. Please update the account in Tenable.io and try again.'
                raise Exception(msg)

        except Exception as exc:
            self.put_msg(exc)
            return False
        else:
            return True

class Proxy(Validator):
    def __init__(self, *args, **kwargs):
        """

        :param validator: user-defined validating function
        """
        super(Proxy, self).__init__()
        self._args = args
        self._kwargs = kwargs

    def validate(self, value, data):
        try:
            if data.get('proxy_enabled', 'false').lower() not in ['0', 'false', 'f']:
                if not data.get('proxy_url'):
                    msg = 'Proxy Host can not be empty'
                    raise Exception(msg)
                elif not data.get('proxy_port'):
                    msg = 'Proxy Port can not be empty'
                    raise Exception(msg)
                elif (data.get('proxy_username') and not data.get('proxy_password')) or (not data.get('proxy_username') and data.get('proxy_password')):
                    msg = 'Please provide both proxy username and proxy password'
                    raise Exception(msg)
                elif not data.get('proxy_type'):
                    msg = 'Proxy Type can not be empty'
                    raise Exception(msg)
        except Exception as exc:
            return False
        else:
            return True
