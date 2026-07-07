
import ta_checkpoint_response_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
import checkpointutility


class CheckConnection(Validator):
    def __init__(self, *args, **kwargs):
        """

        :param validator: user-defined validating function
        """
        super(CheckConnection, self).__init__()
        self._validator = validator
        self._args = args
        self._kwargs = kwargs        
    
    def validate(self, value, data):
        try:
            username = data.get("username")
            password = data.get("password")
            hostname = data.get("hostname")
            key_path = data.get("key_path")
            port = str(data.get("port"))
            os_type = data.get("os_type")
            auth_type = data.get("auth_type")
            domain = data.get("domain")
            upload_path = data.get("upload_path")
            status, msg = checkpointutility.validate_credentials(username=username, password=password,
                                                                 hostname=hostname, key_path=key_path, port=port,
                                                                 os_type=os_type, auth_type=auth_type,domain=domain,upload_path=upload_path)
            if not status:
                raise Exception(msg)
        except Exception as exc:
            self.put_msg(str(exc))
            return False
        else:
            return True

util.remove_http_proxy_env_vars()


fields = [
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
        encrypted=True,
        required=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ),
    field.RestField(
        'key_path',
        encrypted=False,
        required=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ),
    field.RestField(
        'group',
        encrypted=False,
        required=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ),
    field.RestField(
        'hostname',
        encrypted=False,
        required=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ),
    field.RestField(
        'port',
        required=False,
        encrypted=False,
        default=22,
        validator=validator.Number(
            min_val=0,
            max_val=65535,
            is_int=True
        )
    ),
    field.RestField(
        'domain',
        required=False,
        encrypted=False,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ),
    field.RestField(
        'upload_path',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'auth_type',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'os_type',
        required=True,
        encrypted=False,
        default=None,
        validator=CheckConnection()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_checkpoint_response_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )