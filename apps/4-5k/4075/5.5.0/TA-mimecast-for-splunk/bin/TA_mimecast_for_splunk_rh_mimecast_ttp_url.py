import ta_mimecast_for_splunk_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

from mimecast_utils import ValidateMimecastInput

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
        "logs_to_fetch",
        required=True,
        encrypted=False,
        default="all",
        validator=None,
    ),
    field.RestField(
        "credentials",
        required=True,
        encrypted=False,
        default=None,
        validator=ValidateMimecastInput("mimecast_ttp_url"),
    ),
    field.RestField(
        "disabled",
        required=False,
        validator=None,
    ),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "mimecast_ttp_url",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
