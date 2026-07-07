
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
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
            validator.String(
                max_len=255, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^[\w]*$""", 
            )
        )
    )
]

fields = [
    field.RestField(
        'description',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=255, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'api_url',
        required=False,
        encrypted=False,
        default='api.horizon3ai.com',
        validator=validator.String(
            max_len=255, 
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


endpoint = SingleModel(
    'nodezero_accounts',
    model,
    config_name='Accounts',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
