import ta_expanse_declare
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)


util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        )
    ),
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=1,
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_expanse_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
