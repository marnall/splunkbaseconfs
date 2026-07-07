
import ta_cisco_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from utils_account import AccountValidator

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=200, 
        )
    ), 
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=AccountValidator()
    ),
    field.RestField(
        'hostname',
        required=False,
        encrypted=False,
        default="api.cisco.com",
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_cisco_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
