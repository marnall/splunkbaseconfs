import os
import requests
import splunk.admin as admin
import splunk.entity as entity
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.rest_handler.endpoint import (
    validator,
)
from splunktaucclib.splunk_aoblib.rest_helper import TARestHelper
from searchlight_request_handler import SearchLightRequestHandler
from searchlight.api.support import test

from utils.digital_shadows_utility import get_proxy_settings, get_global_setting_account_ids

class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class Utility:
    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def getEntities(self, app_name):
        session_key_obj = GetSessionKey()
        session_key = session_key_obj.session_key
        return entity.getEntities(['admin', 'passwords'], namespace=app_name, owner='nobody', sessionKey=session_key,
                                  search=app_name)

    def getProxy(self, app_name):
        return get_proxy_settings(app_name, self.getEntities(app_name))


class DigitalShadowsPortalUrlValidator(Validator):
    """
        Responsible for validating user entered API Secret & API Key for Old API
    """
    def __init__(self, *args, **kwargs):
        super(DigitalShadowsPortalUrlValidator, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
        self.util = Utility()

    def validate(self, value, data):
        try:
            app_name = self.path.split('/')[-3] if '/' in self.path else self.path.split('\\')[-3]
            if not value.startswith("https://"):
                msg = "Digital Shadows Portal URL should start with 'https://'"
                raise Exception(msg)
            try:
                url = str(data['ds_portal_url']).rstrip('/') + '/api/session-user'
                resp = requests.get(url, auth=(data['access_key'].strip(), data['secret_key'].strip()), proxies=self.util.getProxy(app_name))
            except Exception as e:
                msg = f"Please enter valid Digital Shadows Portal URL or configure valid proxy settings."
                raise Exception(msg)
            if not resp.ok:
                msg = "Please enter valid Digital Shadows Portal URL, API key and API secret."
                raise Exception(msg)

        except Exception:
            self.put_msg(msg)
            return False
        else:
            return True


class DigitalShadowsSearchlightUrlValidator(Validator):
    """
        Responsible for validating user entered API Secret & API Key for new SearchLight API
    """
    def __init__(self, *args, **kwargs):
        super(DigitalShadowsSearchlightUrlValidator, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
        self.util = Utility()

    def validate(self, value, data):
        try:
            app_name = self.path.split('/')[-3] if '/' in self.path else self.path.split('\\')[-3]
            if not value.startswith("https://"):
                msg = "Digital Shadows SearchLight API URL should start with 'https://'"
                raise Exception(msg)
            try:
                proxies = self.util.getProxy(app_name)
                proxy_uri = None
                if proxies:
                    proxy_uri = proxies.get("https")
                rest_helper = TARestHelper()
                request_handler = SearchLightRequestHandler(rest_helper, account_id=data['account_id'].strip(),
                                                            access_key=data['access_key'].strip(),
                                                            secret_key=data['secret_key'].strip(),
                                                            base_url=data['ds_searchlight_api_url'].strip())
                test(request_handler, proxy_uri=proxy_uri)
            except Exception as e:
                msg = "Please enter valid Digital Shadows SearchLight API URL or configure valid proxy settings. Error: {}".format(e)
                raise Exception(msg)

        except Exception:
            self.put_msg(msg)
            return False
        else:
            return True


class DigitalShadowsAccountIDValidator(Validator):
    """
        Responsible for validating DS Account. Same Account ID shouldn't be used again
    """
    def __init__(self, *args, **kwargs):
        super(DigitalShadowsAccountIDValidator, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)

    def validate(self, value, _data):
        try:
            try:
                int(value)
            except ValueError:
                msg = "Invalid format for integer value"
                raise Exception(msg)
            if len(str(value)) == 12:
                app_name = self.path.split('/')[-3] if '/' in self.path else self.path.split('\\')[-3]
                account_ids = get_global_setting_account_ids(app_name)
                if str(value) in account_ids:
                    msg = "Another global account with same Account ID has already been configured"
                    raise Exception(msg)
            else:
                msg = "Account should be 12 digit number"
                raise Exception(msg)
        except Exception:
            self.put_msg(msg)
            return False
        else:
            return True