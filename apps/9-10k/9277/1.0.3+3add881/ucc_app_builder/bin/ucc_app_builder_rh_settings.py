
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging

util.remove_http_proxy_env_vars()


fields_ai_provider = [
    field.RestField(
        'provider',
        required=True,
        encrypted=False,
        default='openrouter',
        validator=None
    ), 
    field.RestField(
        'api_key',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=256, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'base_url',
        required=False,
        encrypted=False,
        default='https://openrouter.ai/api/v1',
        validator=validator.String(
            max_len=255, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'model',
        required=False,
        encrypted=False,
        default='anthropic/claude-sonnet-4.6',
        validator=validator.String(
            max_len=128, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'temperature',
        required=False,
        encrypted=False,
        default='0.3',
        validator=validator.String(
            max_len=8, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'build_model',
        required=False,
        encrypted=False,
        default='anthropic/claude-sonnet-4.6',
        validator=validator.String(
            max_len=128, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'build_temperature',
        required=False,
        encrypted=False,
        default='0.1',
        validator=validator.String(
            max_len=8, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'completion_model',
        required=False,
        encrypted=False,
        default='anthropic/claude-haiku-4.5',
        validator=validator.String(
            max_len=128, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'completion_temperature',
        required=False,
        encrypted=False,
        default='0.1',
        validator=validator.String(
            max_len=8, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'max_iterations',
        required=False,
        encrypted=False,
        default='40',
        validator=validator.String(
            max_len=4, 
            min_len=0, 
        )
    )
]
model_ai_provider = RestModel(fields_ai_provider, name='ai_provider')


endpoint = MultipleModel(
    'ucc_app_builder_settings',
    models=[
        model_ai_provider
    ],
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
