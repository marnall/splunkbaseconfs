
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
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
        default='',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""", 
            ), 
            validator.String(
                max_len=100, 
                min_len=1, 
            )
        )
    )
]

fields = [
    field.RestField(
        'api_host',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'api_key',
        required=False,
        encrypted=True,
        default='',
        validator=None
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='86400',
        validator=None
    ), 
    field.RestField(
        'sourcetype',
        required=False,
        encrypted=False,
        default='cisco:cvi',
        validator=None
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='cisco_cvi',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None, special_fields=special_fields)



endpoint = DataInputModel(
    'sbg_cvi_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
