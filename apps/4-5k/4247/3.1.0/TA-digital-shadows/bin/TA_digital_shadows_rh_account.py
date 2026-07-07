import ta_digital_shadows_declare
from digital_shadows_account_validation import DigitalShadows

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
        'address',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'access_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'secret_key',
        required=True,
        encrypted=True,
        default=None,
        validator=DigitalShadows()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_digital_shadows_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
