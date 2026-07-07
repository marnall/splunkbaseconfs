
import ta_aiops_sfcc_logs_declare

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
        'ocapi_credentials',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'auth_headers',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    ),
    field.RestField(
        'ocapi_shop_ordersearch_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'ocapi_hostname',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'connection_type',
        required=False,
        encrypted=False,
        default='ocapi',
        validator=validator.Pattern(
            regex=r"""^(ocapi|gateway)$""",
        )
    ),
    field.RestField(
        'from_datetime',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'to_datetime',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'delta_period',
        required=False,
        encrypted=False,
        default='10',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=None
    ),
    field.RestField(
        'site_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'time_buffer',
        required=True,
        encrypted=False,
        default='15',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'select_statement',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'host_override',
        required=False,
        encrypted=False,
        default=None,
    )
]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'salesforce_commerce_cloud_orders',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
