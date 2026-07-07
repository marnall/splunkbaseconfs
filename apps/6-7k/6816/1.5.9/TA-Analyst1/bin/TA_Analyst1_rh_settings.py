import ta_analyst1_declare  # noqa:F401
from analyst1_helpers.validators import SplunkKvStoreRest, CorrelationValidator
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

from validators import CronValidator


util.remove_http_proxy_env_vars()


fields_proxy = [
    field.RestField(
        "proxy_enabled", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "proxy_type", required=False, encrypted=False, default="http", validator=None
    ),
    field.RestField(
        "proxy_url",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=4096,
        ),
    ),
    field.RestField(
        "proxy_port",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1,
            max_val=65535,
        ),
    ),
    field.RestField(
        "proxy_username",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=50,
        ),
    ),
    field.RestField(
        "proxy_password",
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
]
model_proxy = RestModel(fields_proxy, name="proxy")


fields_logging = [
    field.RestField(
        "loglevel", required=True, encrypted=False, default="INFO", validator=None
    )
]
model_logging = RestModel(fields_logging, name="logging")


fields_splunk_rest_host = [
    field.RestField(
        "analyst1_indicator_indices_macro",
        required=True,
        encrypted=False,
        default="main",
        validator=None,
    ),
    field.RestField(
        "indicator_fields",
        required=False,
        encrypted=False,
        default="All",
        validator=None,
    ),
    field.RestField(
        "skip_index",
        required=True,
        encrypted=False,
        default=1,
        validator=SplunkKvStoreRest(),
    ),
    field.RestField(
        "full_sync_schedule",
        required=True,
        encrypted=False,
        default="0 0 * * *",
        validator=CronValidator(),
    ),
    field.RestField(
        "diff_sync_schedule",
        required=False,
        encrypted=False,
        default="0 */4 * * *",
        validator=CronValidator(),
    ),
    field.RestField(
        "splunk_username",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200,
            min_len=1,
        ),
    ),
    field.RestField(
        "splunk_password",
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192,
            min_len=1,
        ),
    ),
    field.RestField(
        "splunk_rest_host_url",
        required=False,
        encrypted=False,
        default="localhost",
        validator=validator.Pattern(
            regex="^(?!\\w+:\\/\\/).*",
        ),
    ),
    field.RestField(
        "splunk_rest_port",
        required=False,
        encrypted=False,
        default=8089,
        validator=validator.Number(
            max_val=65535,
            min_val=1,
        ),
    ),
]

model_splunk_rest_host = RestModel(fields_splunk_rest_host, name="splunk_rest_host")


fields_additional_parameters = [
    field.RestField(
        "required_disable_checkbox",
        required=True,
        encrypted=False,
        default=1,
        validator=CorrelationValidator(),
    ),
    field.RestField(
        "enabled_indicator_types",
        required=False,
        encrypted=False,
        default="",
        validator=None,
    ),
    field.RestField(
        "lookup_location_domain",
        required=False,
        encrypted=False,
        default="analyst1_lookup",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_splunk_query_domain",
        required=False,
        encrypted=False,
        default="index=main sourcetype!=analyst1:*",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_fields_to_match_domain",
        required=False,
        encrypted=False,
        default="domain, src, dest",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "lookup_location_email",
        required=False,
        encrypted=False,
        default="analyst1_lookup",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_splunk_query_email",
        required=False,
        encrypted=False,
        default="index=main sourcetype!=analyst1:*",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_fields_to_match_email",
        required=False,
        encrypted=False,
        default="email, user",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "lookup_location_ip",
        required=False,
        encrypted=False,
        default="analyst1_lookup",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_splunk_query_ip",
        required=False,
        encrypted=False,
        default="index=main sourcetype!=analyst1:*",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_fields_to_match_ip",
        required=False,
        encrypted=False,
        default="src, dest",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "lookup_location_file",
        required=False,
        encrypted=False,
        default="analyst1_lookup",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_splunk_query_file",
        required=False,
        encrypted=False,
        default="index=main sourcetype!=analyst1:*",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_fields_to_match_file",
        required=False,
        encrypted=False,
        default="filename, hash",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "lookup_location_string",
        required=False,
        encrypted=False,
        default="analyst1_lookup",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_splunk_query_string",
        required=False,
        encrypted=False,
        default="index=main sourcetype!=analyst1:*",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_fields_to_match_string",
        required=False,
        encrypted=False,
        default="description, comments",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "lookup_location_mutex",
        required=False,
        encrypted=False,
        default="analyst1_lookup",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_splunk_query_mutex",
        required=False,
        encrypted=False,
        default="index=main sourcetype!=analyst1:*",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_fields_to_match_mutex",
        required=False,
        encrypted=False,
        default="mutex",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "lookup_location_httpRequest",
        required=False,
        encrypted=False,
        default="analyst1_lookup",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_splunk_query_httpRequest",
        required=False,
        encrypted=False,
        default="index=main sourcetype!=analyst1:*",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_fields_to_match_httpRequest",
        required=False,
        encrypted=False,
        default="request",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "lookup_location_url",
        required=False,
        encrypted=False,
        default="analyst1_lookup",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_splunk_query_url",
        required=False,
        encrypted=False,
        default="index=main sourcetype!=analyst1:*",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "target_fields_to_match_url",
        required=False,
        encrypted=False,
        default="src, dest",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
]
model_additional_parameters = RestModel(
    fields_additional_parameters, name="additional_parameters"
)


fields_es_threatlist = [
    field.RestField(
        "es_weight_benign_enabled",
        required=False,
        encrypted=False,
        default=True,
        validator=None,
    ),
    field.RestField(
        "es_weight_benign",
        required=False,
        encrypted=False,
        default=1,
        validator=validator.Number(min_val=1, max_val=100),
    ),
    field.RestField(
        "es_weight_lowest_enabled",
        required=False,
        encrypted=False,
        default=True,
        validator=None,
    ),
    field.RestField(
        "es_weight_lowest",
        required=False,
        encrypted=False,
        default=20,
        validator=validator.Number(min_val=1, max_val=100),
    ),
    field.RestField(
        "es_weight_low_enabled",
        required=False,
        encrypted=False,
        default=True,
        validator=None,
    ),
    field.RestField(
        "es_weight_low",
        required=False,
        encrypted=False,
        default=40,
        validator=validator.Number(min_val=1, max_val=100),
    ),
    field.RestField(
        "es_weight_moderate_enabled",
        required=False,
        encrypted=False,
        default=True,
        validator=None,
    ),
    field.RestField(
        "es_weight_moderate",
        required=False,
        encrypted=False,
        default=60,
        validator=validator.Number(min_val=1, max_val=100),
    ),
    field.RestField(
        "es_weight_high_enabled",
        required=False,
        encrypted=False,
        default=True,
        validator=None,
    ),
    field.RestField(
        "es_weight_high",
        required=False,
        encrypted=False,
        default=80,
        validator=validator.Number(min_val=1, max_val=100),
    ),
    field.RestField(
        "es_weight_critical_enabled",
        required=False,
        encrypted=False,
        default=True,
        validator=None,
    ),
    field.RestField(
        "es_weight_critical",
        required=False,
        encrypted=False,
        default=100,
        validator=validator.Number(min_val=1, max_val=100),
    ),
    field.RestField(
        "es_weight_unknown_enabled",
        required=False,
        encrypted=False,
        default=True,
        validator=None,
    ),
    field.RestField(
        "es_weight_unknown",
        required=False,
        encrypted=False,
        default=60,
        validator=validator.Number(min_val=1, max_val=100),
    ),
]
model_es_threatlist = RestModel(fields_es_threatlist, name="es_threatlist")


endpoint = MultipleModel(
    "ta_analyst1_settings",
    models=[
        model_proxy,
        model_logging,
        model_splunk_rest_host,
        model_additional_parameters,
        model_es_threatlist,
    ],
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
