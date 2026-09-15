
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from CYBERHAVEN_utils import CyberhavenHECValidator, NotableAutomationValidator, CyberhavenApiKeyValidator
import logging

util.remove_http_proxy_env_vars()


def _hec_group_fields(source_type):
    return [
        field.RestField(
            f'hec_name_{source_type}',
            required=False,
            encrypted=False,
            default=None,
            validator=validator.String(max_len=50, min_len=1)
        ),
        field.RestField(
            f'index_{source_type}',
            required=False,
            encrypted=False,
            default=None,
            validator=validator.String(max_len=80, min_len=1)
        ),
        field.RestField(
            f'hec_token_{source_type}',
            required=False,
            encrypted=False,
            default=None,
            validator=None
        ),
    ]


fields_hec_settings = [
    field.RestField(
        'tenant_url',
        required=True,
        encrypted=False,
        default=None,
        validator=CyberhavenHECValidator()
    ),
    field.RestField(
        'type',
        required=True,
        encrypted=False,
        default='incidents',
        validator=None
    ),
    field.RestField(
        'macro_indices',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    *_hec_group_fields('audit_logs'),
    *_hec_group_fields('events'),
    *_hec_group_fields('incidents'),
]
model_hec_settings = RestModel(fields_hec_settings, name='hec_settings')


fields_notable_automation = [
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=CyberhavenApiKeyValidator()
    ),
    field.RestField(
        'enable_notable_automation',
        required=False,
        encrypted=False,
        default='0',
        validator=NotableAutomationValidator()
    ),
]
model_notable_automation = RestModel(fields_notable_automation, name='notable_automation')


fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default='0',
        validator=None
    ),
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=validator.Pattern(
            regex=r"""^http$""",
        )
    ),
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Host()
    ),
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Port()
    ),
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(max_len=50)
    ),
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(max_len=8192)
    ),
]
model_proxy = RestModel(fields_proxy, name='proxy')


fields_logging = [
    field.RestField(
        'loglevel',
        required=True,
        encrypted=False,
        default='INFO',
        validator=validator.Pattern(
            regex=r"""^DEBUG|INFO|WARNING|ERROR|CRITICAL$""",
        )
    )
]
model_logging = RestModel(fields_logging, name='logging')


endpoint = MultipleModel(
    'ta-cyberhaven_settings',
    models=[
        model_hec_settings,
        model_notable_automation,
        model_proxy,
        model_logging
    ],
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
