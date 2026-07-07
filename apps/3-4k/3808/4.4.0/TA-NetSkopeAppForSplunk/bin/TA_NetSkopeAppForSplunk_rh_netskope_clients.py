
import ta_netskopeappforsplunk_declare
import const

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

from utils_netskope_clients import NetskopeClientsModel
from netskope_utils import IntervalValidator, QueryValidator, DatetimeValidator, TokenV1Validator

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=IntervalValidator()
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
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=TokenV1Validator()
    ),
    field.RestField(
        'start_datetime',
        required=False,
        encrypted=False,
        default=None,
        validator=DatetimeValidator(label="Start Datetime", max_days_back=const.NETSKOPE_MAX_DAYS_BACK)
    ),
    field.RestField(
        'offset',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'limit',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'failed_window_retries',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'query',
        required=False,
        encrypted=False,
        default=None,
        validator=QueryValidator()
    ),
    field.RestField(
        'api_request_timeout',
        required=True,
        encrypted=False,
        default=180,
        validator=validator.Pattern(
            regex=r"""^[1-9]\d*$""",
        )
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)


endpoint = NetskopeClientsModel(
    'netskope_clients',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
