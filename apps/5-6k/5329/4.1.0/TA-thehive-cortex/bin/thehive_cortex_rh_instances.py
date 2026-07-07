
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging


util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    )
]

fields = [
    field.RestField(
        'account_name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'authentication_type',
        required=True,
        encrypted=False,
        default='api_key',
        validator=validator.String(
            max_len=50, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'type',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=50, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'environment',
        required=True,
        encrypted=False,
        default='PRODUCTION',
        validator=validator.String(
            max_len=50, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'host',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'port',
        required=True,
        encrypted=False,
        default='9000',
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'uri',
        required=False,
        encrypted=False,
        default='/',
        validator=validator.String(
            max_len=255, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'organisation',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default='-',
        validator=validator.String(
            max_len=255, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'proxy_account',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'client_cert',
        required=False,
        encrypted=False,
        default='-',
        validator=validator.String(
            max_len=255, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'ca_cert_path',
        required=False,
        encrypted=False,
        default='-',
        validator=validator.String(
            max_len=255, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'comment',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255, 
            min_len=0, 
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'thehive_cortex_instances',
    model,
    config_name='instances',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
