
import ta_agari_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from utils_account import SetDefaultTime

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""", 
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
        'start_date',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'alert_types',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'failure_data_mode',
        required=True,
        encrypted=False,
        default='off',
        validator=SetDefaultTime()
    ), 
    field.RestField(
        'alert_mode',
        required=True,
        encrypted=False,
        default='alert_details',
        validator=None
    ),
    field.RestField(
        'threat_feeds_mode',
        required=True,
        encrypted=False,
        default='on',
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
    'agari_bp',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
