
import ta_mandiant_threat_intelligence_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

from mati_validator import IndicatorSettings

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
    ), 
    field.RestField(
        'proxy_rdns',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model_proxy = RestModel(fields_proxy, name='proxy')


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


fields_inidcator_settings = [
    field.RestField(
        'mandiant_indicator_index',
        required=False,
        encrypted=False,
        default='main',
        validator=IndicatorSettings()
    ),
    field.RestField(
        'enable_indicator_lookup',
        required=False,
        encrypted=False,
        validator=None
    ),
    field.RestField(
        'mandiant_indicator_time_window',
        required=False,
        encrypted=False,
        default=30,
        validator=validator.Number(
            min_val=1, 
            max_val=90, 
        )
    ),
    field.RestField(
        'mandiant_min_threat_score',
        required=False,
        encrypted=False,
        default=80,
        validator=validator.Number(
            min_val=1, 
            max_val=100, 
        )
    )
]
model_indicator_settings = RestModel(fields_inidcator_settings, name='indicator_settings')


endpoint = MultipleModel(
    'ta_mandiant_threat_intelligence_settings',
    models=[
        model_proxy, 
        model_logging,
        model_indicator_settings
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
