"""REST handler for TA-cyware-ctix settings endpoint."""

import ta_cyware_ctix_declare  # noqa: F401

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
import ta_cyware_ctix.logging_helper as logging_helper
from ta_cyware_ctix.kvstore_helper import SplunkKvStoreValidator
from ta_cyware_ctix.cyware_correlation_validator import CorrelationValidator


util.remove_http_proxy_env_vars()

logger = logging_helper.get_logger("account_handler")

util.remove_http_proxy_env_vars()

correlation_raw_search_query = "index=main sourcetype!=ctix*"


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
    ),
    field.RestField(
        'debug',
        required=False,
        encrypted=False,
        default='false',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')

fields_splunk_rest_host = [
    field.RestField(
        'splunk_username',
        required=False,
        encrypted=False,
        default=None,
        validator=SplunkKvStoreValidator()
    ),
    field.RestField(
        'splunk_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=1,
        )
    ),
    field.RestField(
        'splunk_rest_host_url',
        required=False,
        encrypted=False,
        default="localhost",
        validator=validator.Pattern(
            regex="^(?!\\w+:\\/\\/).*",
        )
    ),
    field.RestField(
        'splunk_rest_port',
        required=False,
        encrypted=False,
        default=8089,
        validator=validator.Number(
            max_val=65535,
            min_val=1,
        )
    )
]
model_splunk_rest_host = RestModel(fields_splunk_rest_host, name="splunk_rest_host")


fields_correlation_settings = [
    field.RestField(
        'required_disable_checkbox',
        required=True,
        encrypted=False,
        default=True,
        validator=CorrelationValidator()
    ),
    field.RestField(
        'enabled_indicator_types',
        required=False,
        encrypted=False,
        default='',
        validator=None
    ),
    field.RestField(
        'match_type',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'datamodel_list',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'target_splunk_query_autonomous_system',
        required=False,
        encrypted=False,
        default=correlation_raw_search_query,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_fields_to_match_autonomous_system',
        required=False,
        encrypted=False,
        default='as_number, as_name',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_splunk_query_domain_name',
        required=False,
        encrypted=False,
        default=correlation_raw_search_query,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_fields_to_match_domain_name',
        required=False,
        encrypted=False,
        default='domain, src, dest',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_splunk_query_email_addr',
        required=False,
        encrypted=False,
        default=correlation_raw_search_query,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_fields_to_match_email_addr',
        required=False,
        encrypted=False,
        default='email, from, to',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_splunk_query_file',
        required=False,
        encrypted=False,
        default=correlation_raw_search_query,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_fields_to_match_file',
        required=False,
        encrypted=False,
        default='file_path, file_name, file_hash',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_splunk_query_ipv4_addr',
        required=False,
        encrypted=False,
        default=correlation_raw_search_query,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_fields_to_match_ipv4_addr',
        required=False,
        encrypted=False,
        default='ip, src, dest',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_splunk_query_ipv6_addr',
        required=False,
        encrypted=False,
        default=correlation_raw_search_query,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_fields_to_match_ipv6_addr',
        required=False,
        encrypted=False,
        default='ip, src, dest',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_splunk_query_network_traffic',
        required=False,
        encrypted=False,
        default=correlation_raw_search_query,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_fields_to_match_network_traffic',
        required=False,
        encrypted=False,
        default='src_ip, dest_ip, src_port, dest_port',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_splunk_query_url',
        required=False,
        encrypted=False,
        default=correlation_raw_search_query,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_fields_to_match_url',
        required=False,
        encrypted=False,
        default='url, domain',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_splunk_query_windows_registry_key',
        required=False,
        encrypted=False,
        default=correlation_raw_search_query,
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    ),
    field.RestField(
        'target_fields_to_match_windows_registry_key',
        required=False,
        encrypted=False,
        default='registry_key, registry_value',
        validator=validator.String(
            max_len=8192,
            min_len=0,
        )
    )
]
model_correlation_settings = RestModel(fields_correlation_settings, name='correlation_settings')

endpoint = MultipleModel(
    'ta_cyware_ctix_settings',
    models=[
        model_proxy,
        model_logging,
        model_splunk_rest_host,
        model_correlation_settings
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
