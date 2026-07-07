
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.splunk_aoblib.rest_migration import ConfigMigrationHandler
import logging

from mandiant_setup import (
  MandiantSavedSearchesManager,
  ValidateTTL,
  MandiantMacrosManager,
  MandiantMatchedEventsManager
)

from mandiant_vuln_setup import GenericVulnValidator

util.remove_http_proxy_env_vars()


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


fields_matched_events = [
    field.RestField(
        'enable_event_matching',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'data_models_to_match',
        required=False,
        encrypted=False,
        default='',
        validator=MandiantMatchedEventsManager()
    ), 
    field.RestField(
        'enable_notable_alerts',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'exclude_unattributed',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'min_ic_score',
        required=True,
        encrypted=False,
        default='80',
        validator=validator.Pattern(
            regex=r"""^[1-9][0-9]?$|^100$""", 
        )
    ), 
    field.RestField(
        'exclude_actions',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z]*$|^[a-zA-Z]*,\s([a-zA-Z]*,\s)*[a-zA-Z]*$""", 
        )
    ), 
    field.RestField(
        'exclude_categories',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'severity_definition',
        required=False,
        encrypted=False,
        default='medium',
        validator=None
    )
]
model_matched_events = RestModel(fields_matched_events, name='matched_events')


fields_vuln_correlation_parameters = [
    field.RestField(
        'enable_vuln_correlation',
        required=False,
        encrypted=False,
        default=None,
        validator=GenericVulnValidator()
    ), 
    field.RestField(
        'mandiant_vuln_advantage_account',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'vuln_indices',
        required=False,
        encrypted=False,
        default='main',
        validator=validator.Pattern(
            regex=r"""^((?:\w+-*\w*),)*(?:\w+-*\w*)$""", 
        )
    ), 
    field.RestField(
        'vuln_src_type',
        required=False,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^((?:[^,\s]+),)*(?:[^,\s]+)$""", 
        )
    ), 
    field.RestField(
        'vuln_fields',
        required=False,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^((?:[^,\s]+),)*(?:[^,\s]+)$""", 
        )
    ), 
    field.RestField(
        'vuln_host_field',
        required=False,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^((?:[^,\s]+),)*(?:[^,\s]+)$""", 
        )
    ), 
    field.RestField(
        'vuln_ttl',
        required=False,
        encrypted=False,
        default='30',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    )
]
model_vuln_correlation_parameters = RestModel(fields_vuln_correlation_parameters, name='vuln_correlation_parameters')


fields_configure_index = [
    field.RestField(
        'job_index',
        required=True,
        encrypted=False,
        default='main',
        validator=MandiantMacrosManager()
    ), 
    field.RestField(
        'iocs_index',
        required=True,
        encrypted=False,
        default='main',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'dtm_alerts_index',
        required=True,
        encrypted=False,
        default='main',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'asm_issues_index',
        required=True,
        encrypted=False,
        default='main',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'asm_entities_index',
        required=True,
        encrypted=False,
        default='main',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'target_index',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    )
]
model_configure_index = RestModel(fields_configure_index, name='configure_index')


endpoint = MultipleModel(
    'ta_mandiant_advantage_settings',
    models=[
        model_logging, 
        model_matched_events, 
        model_vuln_correlation_parameters, 
        model_configure_index
    ],
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
