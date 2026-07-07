
import ta_netapp_eseries_declare
from netapp_eseries_account_validation import WebProxy, BasicAuthentication

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'web_proxy',
        required=True,
        encrypted=False,
        default='',
        validator=WebProxy()
    ), 
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=1, 
            max_len=200, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=BasicAuthentication()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_netapp_eseries_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
