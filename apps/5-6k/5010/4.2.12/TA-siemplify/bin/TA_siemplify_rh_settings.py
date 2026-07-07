import ta_siemplify_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()

fields_mode = [
    field.RestField(
        'mode',
        required=False,
        encrypted=False,
        default='pull',
        validator=None
    )
]
model_mode = RestModel(fields_mode, name='mode')

fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')

fields_authentication = [
    field.RestField(
        'siemplify_api_uri',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'api_key',
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'siemplify_api_uri_secondary',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'api_key_secondary',
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    )
]
model_authentication = RestModel(fields_authentication, name='authentication')


endpoint = MultipleModel(
    'ta_siemplify_settings',
    models=[
        model_mode,
        model_logging, 
        model_authentication
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
