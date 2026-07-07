
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
        'region',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'auth_method',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^client-[^-]*""", 
        )
    ), 
    field.RestField(
        'refresh_token',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'access_token',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'password',
        required=False,
        encrypted=True,
        default='',
        validator=None
    ), 
    field.RestField(
        'xdr_import_time_range',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'incidents',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.Number(
            max_val=900, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'sourcetype',
        required=False,
        encrypted=False,
        default='cisco:xdr:incidents',
        validator=None
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='cisco_xdr',
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
    'sbg_xdr_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
