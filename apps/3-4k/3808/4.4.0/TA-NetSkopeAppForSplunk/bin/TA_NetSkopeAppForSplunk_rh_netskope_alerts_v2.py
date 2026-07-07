
import ta_netskopeappforsplunk_declare
import const

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

from netskope_utils import DatetimeValidator, TokenV2Validator
from utils_netskope_iterator import NetskopeAlertsIteratorModel

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=False,
        encrypted=False,
        default=0,
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
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=TokenV2Validator()
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=None
    ), 
    field.RestField(
        'start_datetime',
        required=False,
        encrypted=False,
        default=None,
        validator=DatetimeValidator(label="Start Datetime", max_days_back=const.NETSKOPE_MAX_DAYS_BACK)
    ),
    field.RestField(
        'end_datetime',
        required=False,
        encrypted=False,
        default=None,
        validator=DatetimeValidator(label="End Datetime", is_iterator_input=True)
    ),
    field.RestField(
        'timeout',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'retry_count',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'fields_include_exclude',
        default="all",
        required=False,
        validator=None
    ),
    field.RestField(
        'fields_include',
        default="",
        required=False,
        validator=None
    ),
    field.RestField(
        'fields_exclude',
        default="",
        required=False,
        validator=None
    ),
    field.RestField(
        'alert_type',
        required=True,
        encrypted=False,
        default="All",
        validator=None
    ),
    field.RestField(
        'is_first_call_all',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_compromisedcredentials',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_ctep',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_dlp',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_malsite',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_malware',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_policy',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_quarantine',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_remediation',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_securityassessment',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_uba',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_watchlist',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_device',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_content',
        required=False,
        encrypted=False,
    )

]
model = RestModel(fields, name=None)



endpoint = NetskopeAlertsIteratorModel(
    'netskope_alerts_v2',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
