
import ta_pihole_dns_declare

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
        'pihole_host',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        )
    ),
    field.RestField(
        'api_pass',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    ),
    field.RestField(
        'api_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        )
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_pihole_dns_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
