
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
        'misp_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""https?://[0-9a-zA-Z-_/\.]+""", 
        )
    ), 
    field.RestField(
        'auth_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.Pattern(
            regex=r"""[a-zA-Z0-9=]+""", 
        )
    ), 
    field.RestField(
        'tls_verify',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'ignore_proxy',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'request_event_limit',
        required=False,
        encrypted=False,
        default=1000,
        validator=validator.Number(
            max_val=1000000, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'request_attribute_limit',
        required=False,
        encrypted=False,
        default=1000,
        validator=validator.Number(
            max_val=1000000, 
            min_val=1, 
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_misp_account',
    model,
    config_name='account'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
