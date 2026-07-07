
import tr_splunk_relay_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from connect_handler import SSEConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields_additional_parameters = [
    field.RestField(
        'sse_connector_port',
        required=False,
        encrypted=False,
        default='8080',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'activation_token',
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'action',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'region',
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    )
]

model_additional_parameters = RestModel(fields_additional_parameters,
                                        name='additional_parameters')


endpoint = MultipleModel(
    'tr_splunk_relay_settings',
    models=[
        model_additional_parameters
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=SSEConfigMigrationHandler,
    )
