
import ta_ps_flashblade_declare
from purestorage_server_validation import *
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'server_address',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(http)s?.*"""
        )
    ), 
    field.RestField(
        'api_token',
        required=True,
        encrypted=True,
        default=None,
        validator=None
    ),
    field.RestField(
        'verify_ssl',
        required=False,
        encrypted=False,
        default=True,
        validator=ValidateAccount()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_ps_flashblade_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
