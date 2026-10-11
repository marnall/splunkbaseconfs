
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
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    )
]

fields = [
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='ssl_cert',
        validator=validator.IndexName()
    ), 
    field.RestField(
        'target_host',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'port',
        required=True,
        encrypted=False,
        default='443',
        validator=validator.Number(
            max_val=65535, 
            min_val=0, 
        )
    ), 
    field.RestField(
        'sni',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'timeout',
        required=False,
        encrypted=False,
        default='10',
        validator=validator.Number(
            max_val=1200, 
            min_val=10, 
        )
    ), 
    field.RestField(
        'verify_cert',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='86400',
        validator=validator.Number(
            max_val=86400, 
            min_val=30, 
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
    'cert_checker',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
