
import ta_endgame_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[1-9]\d*$""",
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
        'endgame_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'endgame_api',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(https).*"""
        )
    ),
    field.RestField(
        'username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'verify_ssl',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    'endgame_api',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
