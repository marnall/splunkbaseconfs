
import ta_cisco_cloud_security_umbrella_addon_declare

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
        default=600,
        validator=validator.Pattern(
            regex=r"""^[1-9]\d{1,3}$""",
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
        'region',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192,
        )
    ), 
    field.RestField(
        'access_key_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=16,
            max_len=256,
        )
    ), 
    field.RestField(
        'secret_access_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=16,
            max_len=256,
        )
    ), 
    field.RestField(
        'bucket_name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'prefix',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'start_date',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(20[0-9]{2})(-)(0[1-9]|1[0-2])(-)(0[1-9]|1[0-9]|2[0-9]|3[0,1])$""", 
        )
    ), 
    field.RestField(
        'event_type',
        required=True,
        encrypted=False,
        default='dns',
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
    'cisco_cloud_security_umbrella_addon',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
