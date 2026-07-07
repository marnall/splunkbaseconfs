
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


fields_global_settings = [
    field.RestField(
        'log_level',
        required=True,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_global_settings = RestModel(fields_global_settings, name='global_settings')


fields_proxy_settings = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'proxy_type',
        required=True,
        encrypted=False,
        default='http',
        validator=None
    ), 
    field.RestField(
        'proxy_rdns',
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
        validator=None
    ), 
    field.RestField(
        'proxy_port',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Number(
                max_val=65535, 
                min_val=1, 
            ), 
            validator.Pattern(
                regex=r"""^[0-9]+$""", 
            )
        )
    ), 
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=50, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    )
]
model_proxy_settings = RestModel(fields_proxy_settings, name='proxy_settings')


endpoint = MultipleModel(
    'google_settings',
    models=[
        model_global_settings, 
        model_proxy_settings
    ],
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
