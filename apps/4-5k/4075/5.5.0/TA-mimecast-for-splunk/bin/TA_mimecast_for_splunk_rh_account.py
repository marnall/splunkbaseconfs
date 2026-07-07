import ta_mimecast_for_splunk_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from mimecast_utils import ValidateMimecastAccount

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "account_code",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "base_url",
        required=True,
        encrypted=False,
        default="https://api.services.mimecast.com",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "client_id",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        ),
    ),
    field.RestField(
        "client_secret",
        required=True,
        encrypted=True,
        default=None,
        validator=ValidateMimecastAccount(),
    ),
    field.RestField(
        "access_token",
        required=False,
        encrypted=True,
        default=None,
        validator=None,
    ),
    field.RestField(
        "expires_at",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    "ta_mimecast_for_splunk_account",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
