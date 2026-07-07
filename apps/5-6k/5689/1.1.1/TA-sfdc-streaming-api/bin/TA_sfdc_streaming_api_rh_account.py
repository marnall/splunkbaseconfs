import ta_sfdc_streaming_api_declare

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
        'domain',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'sandbox',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    )
]

model = RestModel(fields, name=None)

endpoint = SingleModel(
    'ta_sfdc_streaming_api_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
