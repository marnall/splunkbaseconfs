
import ta_cycognito_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from ta_cycognito_validations import IntervalValidator

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=86400,
        validator=IntervalValidator()
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1, 
            max_len=255, 
        )
    ), 
    field.RestField(
        'cycognito_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'asset_types',
        required=True,
        encrypted=False,
        default='*',
        validator=None
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=None
    ),
    field.RestField(
        'collect_removed_assets',
        encrypted=False,
        default=None,
        required=False,
        validator=None
    )
]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'cycognito_assets',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
