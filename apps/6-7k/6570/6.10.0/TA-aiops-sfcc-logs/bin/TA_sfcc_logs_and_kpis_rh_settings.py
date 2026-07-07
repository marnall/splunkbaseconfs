
import ta_sfcc_logs_and_kpis_declare

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
        'license_id',
        required=True,
        encrypted=False,
        default="xxx-xxx-xxx-xxx",
    ),
    field.RestField(
        'license_private_key',
        required=True,
        encrypted=True,
        default="xxx-xxx-xxx-xxx",
    ),
    field.RestField(
        'oauth_2_0_server_url',
        required=True,
        encrypted=False,
        default='https://account.demandware.com/dw/oauth2/access_token',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'license_server_url',
        required=True,
        encrypted=False,
        default='https://license-api-6lybx7sefq-ew.a.run.app',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'license_server_client_id',
        required=True,
        encrypted=True,
        default="xxx-xxx-xxx-xxx",
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')


endpoint = MultipleModel(
    'ta_sfcc_logs_and_kpis_settings',
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
