
import ta_endgame_declare
from account_validation import AccountValidator
from splunk_aoblib.rest_migration import ConfigMigrationHandler


from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        'endgame_api',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(https).*"""
        )
    ),
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=AccountValidator()
    ),
]
model = RestModel(fields, name=None)

endpoint = SingleModel(
    'ta_endgame_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
