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

from utils_netskope_iterator import NetskopeEventsIteratorModel
from utils_account import NETSKOPE_INPUTS
from netskope_utils import DatetimeValidator, TokenV2Validator

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
        'event_type',
        required=True,
        encrypted=False,
        default='connection~application~audit~infrastructure~network~incident~endpoint',
        validator=None
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
        'disabled',
        required=False,
        validator=None
    ),
    field.RestField(
        'is_first_call_page',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_application',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_audit',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_infrastructure',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_network',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_incident',
        required=False,
        encrypted=False,
    ),
    field.RestField(
        'is_first_call_endpoint',
        required=False,
        encrypted=False,
    )

]
model = RestModel(fields, name=None)



endpoint = NetskopeEventsIteratorModel(
    'netskope_events_v2',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )