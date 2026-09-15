
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
            regex=r"""^(DEBUG|INFO|WARNING|ERROR)$""", 
        )
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_settings = [
    field.RestField(
        'override_system_resolver',
        required=False,
        encrypted=False,
        default=0,
        validator=None
    ), 
    field.RestField(
        'default_resolver',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=45, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'default_protocol',
        required=False,
        encrypted=False,
        default='auto',
        validator=None
    )
]
model_settings = RestModel(fields_settings, name='settings')


endpoint = MultipleModel(
    'ta_netkit_settings',
    models=[
        model_logging, 
        model_settings
    ],
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
