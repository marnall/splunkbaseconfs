
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


fields_typesafe = [
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=512, 
            min_len=8, 
        )
    ), 
    field.RestField(
        'base_url',
        required=True,
        encrypted=False,
        default='https://api.typesafe.ai',
        validator=validator.Pattern(
            regex=r"""^https://[^\s]+$""", 
        )
    ), 
    field.RestField(
        'model',
        required=True,
        encrypted=False,
        default='jev-latest',
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    )
]
model_typesafe = RestModel(fields_typesafe, name='typesafe')


fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'proxy_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=4096, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^[A-Za-z0-9._:\-\[\]]+$""", 
            )
        )
    ), 
    field.RestField(
        'proxy_port',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
            is_int=True, 
        )
    )
]
model_proxy = RestModel(fields_proxy, name='proxy')


fields_limits = [
    field.RestField(
        'maxrows',
        required=True,
        encrypted=False,
        default='1000',
        validator=validator.Number(
            max_val=1000000, 
            min_val=1, 
            is_int=True, 
        )
    ), 
    field.RestField(
        'maxrows_ceiling',
        required=True,
        encrypted=False,
        default='10000',
        validator=validator.Number(
            max_val=1000000, 
            min_val=1, 
            is_int=True, 
        )
    ), 
    field.RestField(
        'workers',
        required=True,
        encrypted=False,
        default='8',
        validator=validator.Number(
            max_val=32, 
            min_val=1, 
            is_int=True, 
        )
    ), 
    field.RestField(
        'cache',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'cache_days',
        required=True,
        encrypted=False,
        default='30',
        validator=validator.Number(
            max_val=3650, 
            min_val=1, 
            is_int=True, 
        )
    )
]
model_limits = RestModel(fields_limits, name='limits')


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


endpoint = MultipleModel(
    'jev_for_splunk_settings',
    models=[
        model_typesafe, 
        model_proxy, 
        model_limits, 
        model_logging
    ],
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
