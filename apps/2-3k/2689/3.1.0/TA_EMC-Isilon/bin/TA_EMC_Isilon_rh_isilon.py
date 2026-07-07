
import ta_emc_isilon_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from account_validation import IndexValidator, IntervalValidator
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=3600,
        validator=IntervalValidator()
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='isilon',
        validator=IndexValidator()
    ),
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'endpoint',
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
    'isilon',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
