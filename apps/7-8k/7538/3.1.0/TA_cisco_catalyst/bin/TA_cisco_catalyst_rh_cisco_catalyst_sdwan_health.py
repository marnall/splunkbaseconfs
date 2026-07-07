"""TA-cisco_catalyst_sdwan_health."""

import logging
import import_declare_test  # noqa: F401

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from utils import IntervalValidator

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=None,
        validator=IntervalValidator(),
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
        "sdwan_account",
        required=True,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "health_type",
        required=True,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "logging_level", required=False, encrypted=False, default="INFO", validator=None
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "cisco_catalyst_sdwan_health",
    model,
)


if __name__ == "__main__":

    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
