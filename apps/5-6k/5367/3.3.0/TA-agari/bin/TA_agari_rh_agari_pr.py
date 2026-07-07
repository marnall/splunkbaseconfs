
import ta_agari_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from utils_account import DefaultTimeValidator, IntervalValidator, SetDefaultTime
util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=IntervalValidator()
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1, 
            max_len=80, 
        )
    ), 
    field.RestField(
        'start_date',
        required=False,
        encrypted=False,
        default=None,
        validator=DefaultTimeValidator()
    ),
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=None
    ), 
    field.RestField(
        'data_types',
        required=False,
        encrypted=False,
        default=None,
        validator=SetDefaultTime()
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'agari_pr',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
