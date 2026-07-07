import import_declare_test  # noqa: F401

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
import logging

from Splunk_TA_SAA_rh_account_post_configure import ConnectionSetupPostConfigure

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "base_url",
        required=True,
        encrypted=False,
        default="https://api.twinwave.io",
        validator=validator.Pattern(
            regex=r"""^https://.*$""",
        ),
    ),
    field.RestField("api_key", required=True, encrypted=True, default=None, validator=None),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("splunk_ta_saa_account", model, config_name="account")


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=ConnectionSetupPostConfigure,
    )
