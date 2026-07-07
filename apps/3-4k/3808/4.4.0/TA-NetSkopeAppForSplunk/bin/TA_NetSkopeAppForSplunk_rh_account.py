
import ta_netskopeappforsplunk_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)

from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from utils_account import AccountHandler, AccountModel, TokenV2Validator, TokenValidator

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        'hostname',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""(?i)^(?!https?[:/]).*"""
        )
    ),
    field.RestField(
        'token',
        required=False,
        encrypted=True,
        default=None,
        validator=TokenValidator()
    ),
    field.RestField(
        'token_v2',
        required=False,
        encrypted=True,
        default=None,
        validator=TokenV2Validator()
    )
]
model = RestModel(fields, name=None)

endpoint = AccountModel(
    'ta_netskopeappforsplunk_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AccountHandler,
    )
