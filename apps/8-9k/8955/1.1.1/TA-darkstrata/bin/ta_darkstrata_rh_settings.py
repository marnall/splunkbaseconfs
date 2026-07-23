
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging

util.remove_http_proxy_env_vars()


fields_logging = [
    field.RestField(
        'loglevel',
        required=True,
        encrypted=False,
        default='INFO',
        validator=validator.Pattern(
            regex=r"""^DEBUG|INFO|WARNING|ERROR|CRITICAL$""", 
        )
    )
]
model_logging = RestModel(fields_logging, name='logging')


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


fields_performance = [
    field.RestField(
        'batch_size',
        required=False,
        encrypted=False,
        default='100',
        validator=validator.Number(
            max_val=500, 
            min_val=10, 
        )
    ), 
    field.RestField(
        'request_timeout',
        required=False,
        encrypted=False,
        default='30',
        validator=validator.Number(
            max_val=300, 
            min_val=10, 
        )
    ), 
    field.RestField(
        'max_retries',
        required=False,
        encrypted=False,
        default='3',
        validator=validator.Number(
            max_val=5, 
            min_val=0, 
        )
    ), 
    field.RestField(
        'rate_limit',
        required=False,
        encrypted=False,
        default='0',
        validator=validator.Number(
            max_val=600, 
            min_val=0, 
        )
    ), 
    field.RestField(
        'connection_pooling',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'max_connections',
        required=False,
        encrypted=False,
        default='5',
        validator=validator.Number(
            max_val=20, 
            min_val=1, 
        )
    )
]
model_performance = RestModel(fields_performance, name='performance')


endpoint = MultipleModel(
    'ta_darkstrata_settings',
    models=[
        model_logging, 
        model_proxy, 
        model_performance
    ],
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
