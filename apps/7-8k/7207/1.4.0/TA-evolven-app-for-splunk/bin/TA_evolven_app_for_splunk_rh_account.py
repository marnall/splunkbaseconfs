
import ta_evolven_app_for_splunk_declare
from evolven_server_validation import ValidateAccount
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
        'url',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=ValidateAccount()
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_evolven_app_for_splunk_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
