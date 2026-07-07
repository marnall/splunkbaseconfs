
import ta_cloudknox_declare

from cloudknox_validators import CloudKnoxAuth
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()

fields_cloudknox_cred = [
    field.RestField(
        'cloudknox_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        )
    ),
    field.RestField(
        'account_id',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'access_key',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'secret_key',
        required=True,
        encrypted=True,
        default=None,
        validator=CloudKnoxAuth()
    )
]
model_cloudknox_cred = RestModel(fields_cloudknox_cred, name="cloudknox_credentials")

fields_proxy = [
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
            max_len=4096,
            min_len=0,
        )
    ),
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            max_val=65535,
            min_val=1,
        )
    ),
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=50,
            min_len=0,
        )
    ),
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    )
]
model_proxy = RestModel(fields_proxy, name='proxy')

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


endpoint = MultipleModel(
    'ta_cloudknox_settings',
    models=[
        model_cloudknox_cred,
        model_proxy,
        model_logging
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
