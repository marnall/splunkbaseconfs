
import ta_picus_security_declare

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
        'picus_api_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"^([hH][tT]{2}[pP][sS][:\/]).*(?<!\/)$"
        )
    ), 
    field.RestField(
        'refresh_token',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_picus_security_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
