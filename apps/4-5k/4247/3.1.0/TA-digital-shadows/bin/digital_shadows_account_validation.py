import os
import requests
import io
import json
import splunk.admin as admin
import splunk.entity as entity
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)

from digital_shadows_utility import getProxySettings

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
        return entity.getEntities(['admin', 'passwords'], namespace=app_name, owner='nobody', sessionKey=session_key, search=app_name)

    def getProxy(self, app_name):
        return getProxySettings(app_name, self.getEntities(app_name))



class DigitalShadows(Validator):
    def __init__(self, *args, **kwargs):
        super(DigitalShadows, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
        self.util = Utility()

    def validate(self, value, data):
        try:
            app_name = self.path.split('/')[-3] if '/' in self.path else self.path.split('\\')[-3]
            try:
                session = requests.Session()
                url = 'https://' + str(data['address']).rstrip('/') + '/api/session-user'
                resp = session.get(url, auth=(data['access_key'], data['secret_key']), proxies=self.util.getProxy(app_name),verify=True)
            except Exception:
                msg = "Please enter valid Address or configure valid proxy settings."
                raise Exception(msg)
            if not resp.ok:
                msg = "Please enter valid Address, Access key and Secret key."
                raise Exception(msg)

        except Exception:
            self.put_msg(msg)
            return False
        else:
            return True