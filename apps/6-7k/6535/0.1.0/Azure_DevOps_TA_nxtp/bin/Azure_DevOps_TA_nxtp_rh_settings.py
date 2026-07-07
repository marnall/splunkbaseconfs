
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


fields_additional_parameters = [
    field.RestField(
        'organization',
        required=True,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z]\w{2,100}$""", 
        )
    ), 
    field.RestField(
        'pat',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            max_len=100, 
            min_len=5, 
        )
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')


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
    'azure_devops_ta_nxtp_settings',
    models=[
        model_additional_parameters, 
        model_logging
    ],
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
