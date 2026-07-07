import ta_opswat_metaaccess_declare

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
        'host',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        )
    ),
    field.RestField(
        'auth_endpoint',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        )
    ),
    field.RestField(
        'client_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    ),
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_opswat_metaaccess_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
