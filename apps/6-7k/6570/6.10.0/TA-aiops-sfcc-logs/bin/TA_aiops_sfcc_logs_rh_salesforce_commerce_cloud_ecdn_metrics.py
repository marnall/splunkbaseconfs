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
        "ocapi_credentials",
        required=True,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "ocapi_hostname",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "ocapi_endpoint",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "zone",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "from_datetime",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "to_datetime",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "filter_pattern",
        required=False,
        encrypted=False,
        default="(static|favicon)",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "time_buffer",
        required=False,
        encrypted=False,
        default="60",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "delta_period",
        required=False,
        encrypted=False,
        default="300",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)
endpoint = DataInputModel(
    "salesforce_commerce_cloud_ecdn_metrics",
    model,
)
if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
