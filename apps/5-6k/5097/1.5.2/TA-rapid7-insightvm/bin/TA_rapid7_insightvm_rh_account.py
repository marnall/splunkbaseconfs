
import ta_rapid7_insightvm_declare

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
        'region',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=2,
            max_len=3,
        )
    ), 
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=36,
            max_len=36,
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_rapid7_insightvm_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
