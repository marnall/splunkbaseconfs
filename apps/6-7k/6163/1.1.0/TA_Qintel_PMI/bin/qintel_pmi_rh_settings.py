import app_qintel_pmi_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()

fields_pmi = [
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'pmi_api_url',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
]

fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]

model_pmi = RestModel(fields_pmi, name='pmi')
model_logging = RestModel(fields_logging, name='logging')


endpoint = MultipleModel(
    'qintel_pmi_settings',
    models=[
        model_pmi,
        model_logging,
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
