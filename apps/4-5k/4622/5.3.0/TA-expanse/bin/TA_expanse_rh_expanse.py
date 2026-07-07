import ta_expanse_declare

import datetime
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)

util.remove_http_proxy_env_vars()


def start_date_validator():
    validator.Datetime(
        datetime_format='%Y-%m-%d'
    )


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=3600,
        validator=validator.Number(
            max_val=432000,
            min_val=3600,
        )
    ),
    field.RestField(
        'use_advanced_auth',
        required=True,
        encrypted=False,
        default=False,
        validator=None
    ),
    field.RestField(
        'token',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'server_url',
        required=True,
        encrypted=False,
        default='https://api-{fqdn}',
        validator=validator.Pattern(
            regex="^https://"
        )
    ),
    field.RestField(
        'api_key_id',
        required=True,
        encrypted=False,
        default=False,
        validator=None
    ),

    field.RestField(
        'start_date_utc',
        required=True,
        encrypted=False,
        default=datetime.datetime.now().strftime("%Y-%m-%d"),
        validator=validator.Datetime(
            datetime_format='%Y-%m-%d'
        )
    ),
    field.RestField(
        'utc_offset',
        required=False,
        encrypted=False,
        default=0.0,
        validator=validator.Number(
            min_val=-12.0,
            max_val=14.0
        )
    ),
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'enable_alert_updates',
        encrypted=False,
        required=False,
        default=False,
        # The below validator checks that the 'index' field is not blank if 'enable_alert_updates' is checked
        validator=validator.RequiresIf(
            fields=['index'],
            condition=lambda x, _: x == '1'
        )
    ),
    field.RestField(
        'alert_severity',
        encrypted=False,
        required=False,
        default='high',
    ),
    field.RestField(
        'index',
        required=False,
        encrypted=False,
        default='default',
        validator=validator.String(
            max_len=80,
            min_len=1,
        )
    ),
    field.RestField(
        'enable_assets',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ),
    field.RestField(
        'enable_services',
        encrypted=False,
        required=False,
        default=False,
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
    'expanse',
    model,
)

if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
