import ta_aiops_sfcc_logs_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""",
        ),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.String(
            min_len=1,
            max_len=80,
        ),
    ),
    field.RestField(
        "data_type",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(catalog|inventory|pricebook|navigation-catalog|site-preferences|audit_log)$""",
        ),
    ),
    field.RestField(
        "events_sourcetype",
        required=False,
        encrypted=False,
        default=None,
    ),
    field.RestField(
        "events_host",
        required=False,
        encrypted=False,
        default=None,
    ),
    field.RestField(
        "auth_type",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.Pattern(
            regex=r"""^(basic|oauth|ssh_key)$""",
        ),
    ),
    field.RestField(
        "account",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=1024,
        ),
    ),
    field.RestField(
        "remote_host",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(https)://""",
        ),
    ),
    field.RestField("remote_directories", required=True, encrypted=False, default=None),
    field.RestField(
        "remote_directory_wildcard", required=True, encrypted=False, default="*"
    ),
    field.RestField(
        "remote_directory_depth", required=True, encrypted=False, default="1"
    ),
    field.RestField("days_threshold", required=False, encrypted=False, default="1"),
    field.RestField(
        "variation_attributes_to_include", required=False, encrypted=False, default=None
    ),
    field.RestField(
        "custom_attributes_to_include", required=False, encrypted=False, default=None
    ),
    field.RestField(
        "product_additional_attributes_to_include",
        required=False,
        encrypted=False,
        default=None,
    ),
    field.RestField(
        "ingest_catalog_variation_groups",
        required=False,
        encrypted=False,
        default=None,
    ),
    field.RestField(
        "audit_log_object_type_filters",
        required=False,
        encrypted=False,
        default=None,
    ),
    field.RestField(
        "catalog_timezone",
        required=False,
        encrypted=False,
        default="UTC+00:00",
    ),
    field.RestField(
        "pricebook_timezone",
        required=False,
        encrypted=False,
        default="UTC+00:00",
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "salesforce_commerce_cloud_etl",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
