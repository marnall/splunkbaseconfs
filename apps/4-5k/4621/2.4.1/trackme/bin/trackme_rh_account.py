import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from trackme_rh_account_handler import CustomRestHandlerCreateRemoteAccount
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "splunk_url",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^https://.*$""",
        ),
    ),
    field.RestField(
        "bearer_token",
        required=True,
        encrypted=True,
        default=None,
        validator=validator.Pattern(
            regex=r"""^.{100,}$""",
        ),
    ),
    field.RestField(
        "app_namespace",
        required=True,
        encrypted=False,
        default="search",
        validator=validator.Pattern(
            regex=r"""^.+$""",
        ),
    ),
    field.RestField(
        "rbac_roles",
        required=True,
        encrypted=False,
        default="admin,sc_admin,trackme_user,trackme_power,trackme_admin",
        validator=validator.Pattern(
            regex=r"""^.+$""",
        ),
    ),
    field.RestField(
        "timeout_connect_check",
        required=False,
        encrypted=False,
        default="15",
        validator=validator.Pattern(
            regex=r"""^\d*$""",
        ),
    ),
    field.RestField(
        "timeout_search_check",
        required=False,
        encrypted=False,
        default="300",
        validator=validator.Pattern(
            regex=r"""^\d*$""",
        ),
    ),
    field.RestField(
        "retry_enabled",
        required=False,
        encrypted=False,
        default="1",
        validator=validator.Pattern(
            regex=r"""^(1|0)$""",
        ),
    ),
    field.RestField(
        "retry_max_total_time",
        required=False,
        encrypted=False,
        default="30",
        validator=validator.Pattern(
            regex=r"""^\d*$""",
        ),
    ),
    field.RestField(
        "retry_initial_delay",
        required=False,
        encrypted=False,
        default="2",
        validator=validator.Pattern(
            regex=r"""^\d*$""",
        ),
    ),
    field.RestField(
        "retry_backoff_multiplier",
        required=False,
        encrypted=False,
        default="2.0",
        validator=validator.Pattern(
            regex=r"""^(\d+\.?\d*|\.\d+)$""",
        ),
    ),
    field.RestField(
        "retry_max_attempts",
        required=False,
        encrypted=False,
        default="10",
        validator=validator.Pattern(
            regex=r"""^\d*$""",
        ),
    ),
    field.RestField(
        "token_rotation_enablement",
        required=True,
        encrypted=False,
        default="0",
        validator=validator.Pattern(
            regex=r"""^(1|0)$""",
        ),
    ),
    field.RestField(
        "token_rotation_frequency",
        required=False,
        encrypted=False,
        default="30",
        validator=validator.Pattern(
            regex=r"""^\d*$""",
        ),
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("trackme_account", model, config_name="account")


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CustomRestHandlerCreateRemoteAccount,
    )
