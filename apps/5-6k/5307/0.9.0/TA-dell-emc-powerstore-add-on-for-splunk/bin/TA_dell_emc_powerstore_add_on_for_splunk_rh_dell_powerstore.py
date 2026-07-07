
import ta_dell_emc_powerstore_add_on_for_splunk_declare

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
        'ip_address',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
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
        'compute',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'migration',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'monitoring',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'protection',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'settings',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'storage',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'support',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'system_and_hardware',
        required=False,
        encrypted=False,
        default=None,
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
    'dell_powerstore',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
