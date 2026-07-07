
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


fields_additional_parameters = [
    field.RestField(
        'auth_type',
        required=True,
        encrypted=False,
        default='PRIVATE_TOKEN',
        validator=None
    ), 
    field.RestField(
        'auth_string',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=200, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'authorization_conf_url',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=2000, 
            min_len=0, 
        )
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')


endpoint = MultipleModel(
    'ta_saml_manager_settings',
    models=[
        model_logging, 
        model_additional_parameters
    ],
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
