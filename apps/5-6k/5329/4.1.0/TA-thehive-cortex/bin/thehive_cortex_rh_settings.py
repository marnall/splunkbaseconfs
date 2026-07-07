
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


fields_settings = [
    field.RestField(
        'cortex_max_jobs',
        required=False,
        encrypted=False,
        default='100',
        validator=validator.Number(
            max_val=10000, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'cortex_sort_jobs',
        required=False,
        encrypted=False,
        default='-createdAt',
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'thehive_default_instance',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'thehive_max_cases',
        required=False,
        encrypted=False,
        default='1000',
        validator=validator.Number(
            max_val=10000, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'thehive_sort_cases',
        required=False,
        encrypted=False,
        default='-startDate',
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'thehive_max_alerts',
        required=False,
        encrypted=False,
        default='1000',
        validator=validator.Number(
            max_val=10000, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'thehive_sort_alerts',
        required=False,
        encrypted=False,
        default='-date',
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'splunk_es_alerts_index',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'thehive_ttp_catalog_name',
        required=False,
        encrypted=False,
        default='Enterprise Attack',
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'thehive_creation_attachment_prefix',
        required=False,
        encrypted=False,
        default='events_',
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'thehive_creation_max_retry',
        required=False,
        encrypted=False,
        default='2',
        validator=validator.Number(
            max_val=10, 
            min_val=0, 
        )
    ), 
    field.RestField(
        'splunk_sanitize_backslashes',
        required=False,
        encrypted=False,
        default='ENABLED',
        validator=validator.String(
            max_len=20, 
            min_len=1, 
        )
    )
]
model_settings = RestModel(fields_settings, name='settings')


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
    'thehive_cortex_settings',
    models=[
        model_settings, 
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
