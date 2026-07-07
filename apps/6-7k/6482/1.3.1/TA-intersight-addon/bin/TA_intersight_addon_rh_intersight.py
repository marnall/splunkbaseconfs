
import ta_intersight_addon_declare

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
        'intersight_hostname',
        required=True,
        encrypted=False,
        default='intersight.com',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'validate_ssl',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'api_key_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'api_secret_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'enable_aaa_audit_records',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'enable_alarms',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'inventory',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'inventory_interval',
        required=False,
        encrypted=False,
        default='120',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
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
    'intersight',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
