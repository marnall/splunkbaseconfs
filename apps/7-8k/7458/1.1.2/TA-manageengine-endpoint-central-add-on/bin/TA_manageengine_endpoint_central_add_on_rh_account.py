
import ta_manageengine_endpoint_central_add_on_declare

from manageengine_ec_configuration_validator import *
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()




fields = [
    field.RestField(
        'endpointcenteralserver',
        required=True,
        encrypted=False,
        default='tenale_io',
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'server_url',
        required=False,
        encrypted=False,
        default=None,
        validator=ServerURLValidator()
    ), 
    field.RestField(
        'op_server_url',
        required=False,
        encrypted=False,
        default=None,
        validator=ServerURLValidator()
    ),
    field.RestField(
        'zoho_accounts_server_uri',
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    ),
    field.RestField(
        'auth_token',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'verify_cert',
        required=False,
        encrypted=False,
        default=True
    ),
    field.RestField(
        'input_data',
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    ),
    field.RestField(
        'service_account',
        required=False,
        encrypted=True,
        default=None,
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_manageengine_endpoint_central_add_on_account',
    model
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
