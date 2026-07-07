
import ta_netskopeappforsplunk_declare

import const
from datetime import datetime
from netskope_utils import DatetimeValidator
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from utils_settings import SettingsValidator, EmailFieldValidator

util.remove_http_proxy_env_vars()


fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ),
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=4096,
        )
    ),
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1,
            max_val=65535,
        )
    ),
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=50,
        )
    ),
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    )
]
model_proxy = RestModel(fields_proxy, name='proxy')


fields_logging = [
    field.RestField(
        'loglevel',
        required=True,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_additional_parameters = [
    field.RestField(
        'base_event_type',
        required=False,
        encrypted=False,
        default='index=main',
        validator=SettingsValidator()
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')

fields_scripted_input_parameters = [
    field.RestField(
        'account_name',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'type',
        required=True,
        encrypted=False,
        default="connection~application",
        validator=None
    ),
    field.RestField(
        'start_datetime',
        required=True,
        encrypted=False,
        default=None,
        validator=DatetimeValidator(label="Start Datetime", max_days_back=const.NETSKOPE_MAX_DAYS_BACK)
    ),
    field.RestField(
        'user_end_datetime',
        required=False,
        encrypted=False,
        default=None,
        validator=DatetimeValidator(label="User End Datetime", is_scripted_input=True, is_iterator_input=True)
    ),
    field.RestField(
        'data_collection_window',
        required=True,
        encrypted=False,
        default=60,
        validator=None
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'max_active_inputs',
        required=True,
        encrypted=False,
        default=5,
        validator=None
    )
]
model_scripted_input_parameters = RestModel(fields_scripted_input_parameters, name='scripted_input_parameters')


fields_email_notification = [
    field.RestField(
        'email_enable',
        required=False,
        encrypted=False,
        default=None,
        validator=EmailFieldValidator()
    ),
    field.RestField(
        'email_address',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'notify_after',
        required=False,
        encrypted=False,
        default=24,
        validator=None
    ),
    field.RestField(
        'smtp_server',
        required=False,
        encrypted=False,
        validator=None
    ),
    field.RestField(
        'additional_message',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'enable_throttle',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'throttle_duration',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model_email_notification = RestModel(fields_email_notification, name='email_notification')


endpoint = MultipleModel(
    'ta_netskopeappforsplunk_settings',
    models=[
        model_proxy,
        model_logging,
        model_additional_parameters,
        model_email_notification,
        model_scripted_input_parameters,
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
