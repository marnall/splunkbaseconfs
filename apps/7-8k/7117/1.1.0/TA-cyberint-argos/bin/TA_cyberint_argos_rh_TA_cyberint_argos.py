
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
        default=None,
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
        'client_name',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'instance_domain',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'environment',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^([\w\-]+([ _\-]?[\w\-]+)*,?[ ]?)+$""", 
        )
    ), 
    field.RestField(
        'types',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'severities',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'statuses',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'start_time',
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
            max_val=604800, 
            min_val=30, 
        )
    ), 
    field.RestField(
        'max_fetch',
        required=True,
        encrypted=False,
        default='100',
        validator=validator.Number(
            max_val=100, 
            min_val=10, 
        )
    ), 
    field.RestField(
        'include_csv',
        required=False,
        encrypted=False,
        default=0,
        validator=None
    ), 
    field.RestField(
        'account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            max_len=150, 
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
    'TA_cyberint_argos',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
