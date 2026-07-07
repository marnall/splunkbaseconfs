
import import_declare_test  # noqa F401

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from xmcyber_datetime_validation import DateTimeValidator
from splunktaucclib.rest_handler import admin_external, util
from xmcyber_delete_checkpoint_rh import DeleteCheckpointRestHandler
import logging

util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""",
            ),
            validator.String(
                max_len=150,
                min_len=1,
            )
        )
    )
]

fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='86400',
        validator=validator.Number(
            max_val=604800,
            min_val=21600,
        )
    ),
    field.RestField(
        'index',
        required=False,
        encrypted=False,
        default='default',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9][a-zA-Z0-9\\_\\-]*$""",
            ),
            validator.String(
                max_len=80,
                min_len=1,
            )
        )
    ),
    field.RestField(
        'account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'time_id',
        required=True,
        encrypted=False,
        default=None,
        validator=DateTimeValidator()
    ),

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = DataInputModel(
    'audit_trail',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=DeleteCheckpointRestHandler,
    )
