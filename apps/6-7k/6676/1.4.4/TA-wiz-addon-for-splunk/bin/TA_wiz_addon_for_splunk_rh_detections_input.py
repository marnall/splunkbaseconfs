
import ta_wiz_addon_for_splunk_declare

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
        validator=validator.Number(
            min_val=300,
            max_val=86400,
            is_int=True
        )
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
        'wiz_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'severity',
        required=True,
        encrypted=False,
        default='CRITICAL~HIGH~MEDIUM~LOW~INFORMATIONAL',
        validator=None
    ), 
    field.RestField(
        'project_id',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192, 
        )
    ),
    field.RestField(
        'historical_polling_days',
        required=True,
        encrypted=False,
        default='7',
        validator=validator.Number(
            min_val=1,
            max_val=90,
            is_int=True
        )
    ),
    field.RestField(
        'include_triggering_events',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),    field.RestField(
        'request_timeout',
        required=False,
        encrypted=False,
        default='180',
        validator=validator.Number(
            min_val=1,
            max_val=3600,
            is_int=True
        )
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'detections_input',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
