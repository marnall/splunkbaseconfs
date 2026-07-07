import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from TA_cisco_cybervision_server_validation import ValidateAccount
from TA_cisco_cybervision_rh_account_cleanup import AccountCleanUpHandler
import logging


util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        "name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=50,
                min_len=1,
            ),
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""",
            ),
        ),
    )
]

fields = [
    field.RestField(
        "copy_account_name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=50,
                min_len=1,
            ),
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""",
            ),
        ),
    ),
    field.RestField(
        "ip_address",
        required=True,
        encrypted=False,
        default="",
        validator=ValidateAccount(),
    ),
    field.RestField(
        "api_token",
        required=True,
        encrypted=True,
        default="",
        validator=validator.String(
            max_len=8192,
            min_len=0,
        ),
    ),
    field.RestField(
        "use_ca_cert", required=False, encrypted=False, default=False, validator=None
    ),
    field.RestField(
        "custom_certificate",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    "ta_cisco_cybervision_account",
    model,
    config_name="account",
    need_reload=False,
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AccountCleanUpHandler,
    )
