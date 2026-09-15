
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
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z]\w*$""", 
        )
    )
]

fields = [
    field.RestField(
        'domain_group',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'targets',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'record_types',
        required=True,
        encrypted=False,
        default='A,AAAA',
        validator=None
    ), 
    field.RestField(
        'resolver',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'timeout_ms',
        required=False,
        encrypted=False,
        default='5000',
        validator=validator.Number(
            max_val=60000, 
            min_val=1, 
            is_int=True, 
        )
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.Number(
            max_val=86400, 
            min_val=10, 
            is_int=True, 
        )
    ), 
    field.RestField(
        'index',
        required=False,
        encrypted=False,
        default='default',
        validator=validator.IndexName()
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None, special_fields=special_fields)



endpoint = DataInputModel(
    'netkit_dns_probe',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
