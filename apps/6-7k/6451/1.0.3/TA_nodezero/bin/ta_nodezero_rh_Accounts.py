
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
        'example_help_link',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'nodezero_accounts',
    model,
    config_name='Accounts'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
