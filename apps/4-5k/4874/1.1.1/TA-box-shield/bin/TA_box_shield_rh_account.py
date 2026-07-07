
import ta_box_shield_declare
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from account_validation import AccountValidator

util.remove_http_proxy_env_vars()


fields = [

    field.RestField(
        'client_id',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
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
        'access_token',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=64,
        )
    ),
    field.RestField(
        'refresh_token',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=64,
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_box_shield_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
