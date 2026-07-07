
import ta_jamf_pro_devices_and_analytics_by_loonsecio_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_additional_parameters = [
    field.RestField(
        'loonsecio_base_url',
        required=False,
        encrypted=False,
        default='api.loonsec.io',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'loonsecio_client_id',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'loonsecio_client_secret',
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'sla_days_critical',
        required=False,
        encrypted=False,
        default='30',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'sla_days_high',
        required=False,
        encrypted=False,
        default='30',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'sla_days_medium',
        required=False,
        encrypted=False,
        default='90',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'sla_days_low',
        required=False,
        encrypted=False,
        default='180',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'kv_store_pre_pend',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')


endpoint = MultipleModel(
    'ta_jamf_pro_devices_and_analytics_by_loonsecio_settings',
    models=[
        model_logging, 
        model_additional_parameters
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
