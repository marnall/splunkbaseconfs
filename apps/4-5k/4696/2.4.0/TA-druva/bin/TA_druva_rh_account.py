
import ta_druva_declare

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
        'cloud_type',
        required=True,
        encrypted=False,
        default='apis',
        validator=None
    ),
    field.RestField(
        'username',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=200, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_druva_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
