
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
        'interval',
        required=True,
        encrypted=False,
        default='600',
        validator=validator.Number(
            max_val=86400, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.Pattern(
            regex=r"""^([0-9a-z]{8})-([0-9a-z]{4}-){3}[0-9a-z]{12}$""", 
        )
    ), 
    field.RestField(
        'page_size',
        required=True,
        encrypted=False,
        default='10000',
        validator=validator.Number(
            max_val=10000, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'chunk_size',
        required=True,
        encrypted=False,
        default='10000',
        validator=validator.Number(
            max_val=10000, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'request_timeout',
        required=True,
        encrypted=False,
        default='60',
        validator=validator.Number(
            max_val=3600, 
            min_val=1, 
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
    'proofpoint_web_isolation',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
