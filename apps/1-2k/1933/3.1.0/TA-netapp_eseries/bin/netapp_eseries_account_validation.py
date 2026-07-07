import os
import requests
import requests.packages.urllib3 as urllib3

import splunk.admin as admin
import splunk.entity as entity
from splunktaucclib.rest_handler.endpoint.validator import Validator

from netapp_eseries_utility import getProxySettings
from netapp_eseries_utility import get_verify_ssl

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class GetSessionKey(admin.MConfigHandler):
    """Get Session Key Class."""

    def __init__(self):
        """Initialize Session Key Object."""
        self.session_key = self.getSessionKey()


class Utility:
    """Utility Class."""

    def __init__(self, *args, **kwargs):
        """Initialize Object."""
        self._args = args
        self._kwargs = kwargs

    def getProxy(self, app_name):
        """Get Proxy."""
        return getProxySettings(app_name, self.getEntities(app_name))

    def getEntities(self, app_name):
        """Get Entities."""
        session_key_obj = GetSessionKey()
        session_key = session_key_obj.session_key
        return entity.getEntities(['admin', 'passwords'], namespace=app_name, owner='nobody', sessionKey=session_key,
                                  search=app_name)


class WebProxy(Validator):
    """Web Proxy class."""

    def __init__(self, *args, **kwargs):
        """Initialize object."""
        super(WebProxy, self).__init__()
        self._args = args
        self._kwargs = kwargs

    def validate(self, value, data):
        """Validate  WebProxy."""
        value.strip('/')
        try:
            if "://" in value:
                msg = "Protocols are not allowed in Web Proxy field."
                raise Exception(msg)
        except Exception:
            self.put_msg(msg)
            return False
        else:
            data["web_proxy"] = value.strip('/')
            return True


class BasicAuthentication(Validator):
    """Basic Authentication class."""

    def __init__(self, *args, **kwargs):
        """Initialize object."""
        super(BasicAuthentication, self).__init__()
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
        self.util = Utility()

    def validate(self, value, data):
        """Validate Account."""
        app_name = self.path.split('/')[-3] if '/' in self.path else self.path.split('\\')[-3]

        headers = {
            'Content-Type': "application/json",
        }

        auth = (data["username"], data["password"])

        if 'verify_ssl' not in data:
            verify_ssl = get_verify_ssl()
        else:
            verify_ssl = False if data["verify_ssl"] in ["0", "False", "F", "false", "f"] else True

        try:
            session = requests.Session()
            req = session.get("https://" + data["web_proxy"] + "/devmgr/v2/storage-systems", auth=auth, headers=headers,
                              proxies=self.util.getProxy(app_name), verify=verify_ssl, timeout=10)
            if req.status_code != 200:
                msg = "Please enter valid Web Proxy, Username and Password."
                self.put_msg(msg)
                return False
        except Exception:
            msg = "Please enter valid web proxy or configure valid proxy settings or verify SSL certificate."
            self.put_msg(msg)
            return False
        return True
