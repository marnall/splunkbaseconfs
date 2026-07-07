
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from Splunk_TA_Appdynamics_BaseRestHandler import BaseRestHandler
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
        'type',
        required=True,
        encrypted=False,
        default='License',
        validator=None
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=3600,
        validator=validator.Number(
            max_val=6000000, 
            min_val=60, 
        )
    ), 
    field.RestField(
        'index',
        required=False,
        encrypted=False,
        default='default',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9][a-zA-Z0-9\\_\\-]*$""", 
            ), 
            validator.String(
                max_len=80, 
                min_len=1, 
            )
        )
    ), 
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'duration',
        required=True,
        encrypted=False,
        default='1440',
        validator=None
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None, special_fields=special_fields)



endpoint = DataInputModel(
    'appdynamics_licenses',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=BaseRestHandler,
    )
