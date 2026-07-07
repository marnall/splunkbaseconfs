
import ta_infoblox_api_declare

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
        'requested_fields',
        required=True,
        encrypted=False,
        default='configure_for_dhcp,host,ipv4addr,mac',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'item_limit',
        required=True,
        encrypted=False,
        default='1000',
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
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'infoblox_ipv4_addresses',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
