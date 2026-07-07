
import soctoolkit_connector_ta_nxtp_declare

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
        "start_from",
        required=True,
        encrypted=False,
        default="2019-09-16 00:00:00",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "soc_toolkit_audit_log",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
