
import ta_cherwell_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from cherwell_account_validation import *
import cherwellutility
import splunk.admin as admin
import splunk.entity as entity

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
        return cherwellutility.getProxySettings(app_name, self.getEntities(app_name))

class CheckConnection(Validator):
    def __init__(self, *args, **kwargs):
        """

        :param validator: user-defined validating function
        """
        super(CheckConnection, self).__init__()
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.util = Utility()
        self.path = os.path.abspath(__file__)

    def validate(self, value, data):
        ipaddress = data.get("ipaddress")
        username = data.get("username")
        password = data.get("password")
        clientid = data.get("clientid")
        ssl_verify = data.get("ssl_verify")
        url_scheme = data.get("url_scheme")
        app_name = self.path.split('/')[-3] if '/' in self.path else self.path.split('\\')[-3]
        proxies = self.util.getProxy(app_name)
        if not proxies:
            proxies = None
        status, msg = cherwellutility.validate_credentials(url_scheme=url_scheme, ipaddress=ipaddress, username=username, password=password,
                                                             clientid=clientid, ssl_verify=ssl_verify, proxies=proxies)
        if not status:
           self.put_msg(msg)
        else:
            return True

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        'url_scheme',
        required=True,
        encrypted=False,
        default="https",
        validator=validator.Pattern(
            regex=r"""^(http|https)$""",
            )
    ),
    field.RestField(
        'ipaddress',
        required=True,
        encrypted=False,
        default=None,
        validator=Address()
    ),
	field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ),
	field.RestField(
        'ssl_verify',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ),
    field.RestField(
        'clientid',
        required=True,
        encrypted=True,
        default=None,
        validator=CheckConnection()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_cherwell_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
