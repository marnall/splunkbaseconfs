import ta_cisco_threat_response_declare  # noqa: F401

from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)

from connect_handler import ConnectConfigMigrationHandler

util.remove_http_proxy_env_vars()

fields_additional_parameters = [
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
        'client_password',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'region',
        required=False,
        encrypted=False,
        default='US',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'response_indexing',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'index_name',
        required=False,
        encrypted=False,
        default='main',
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    ),
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ),
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=4096,
        )
    ),
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1,
            max_val=65535,
        )
    ),
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=50,
        )
    ),
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    )
]
model_additional_parameters = RestModel(fields_additional_parameters,
                                        name='additional_parameters')

endpoint = MultipleModel(
    'ta_cisco_threat_response_settings',
    models=[
        model_additional_parameters
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConnectConfigMigrationHandler,
    )
