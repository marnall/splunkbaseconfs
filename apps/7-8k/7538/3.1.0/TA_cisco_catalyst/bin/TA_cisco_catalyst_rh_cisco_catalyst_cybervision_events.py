"""TA-cisco_catalyst_cybervision_events."""
import logging
import import_declare_test  # noqa: F401

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from utils import CyberVisionModel, IntervalValidator, ValidateStartDate

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=IntervalValidator()
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1,
            max_len=80,
        )
    ),
    field.RestField(
        'cyber_vision_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),

    field.RestField(
        'start_date',
        required=True,
        encrypted=False,
        default=None,
        validator=ValidateStartDate()
    ),

    field.RestField(
        'logging_level',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    ),

    field.RestField(
        'page_size',
        required=False,
        encrypted=False,
        default=10,
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""",
        )
    ),

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)


endpoint = CyberVisionModel(
    'cisco_catalyst_cybervision_events',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
