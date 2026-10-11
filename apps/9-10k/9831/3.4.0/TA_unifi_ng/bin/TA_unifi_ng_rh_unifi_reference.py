
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
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
                max_len=100,
                min_len=1,
            )
        )
    )
]

fields = [
    field.RestField(
        'account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='86400',
        validator=validator.Pattern(
            regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""",
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
        'collect_countries',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ),
    field.RestField(
        'collect_dpi_applications',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ),
    field.RestField(
        'collect_dpi_categories',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ),
    field.RestField(
        'page_size',
        required=False,
        encrypted=False,
        default='200',
        validator=validator.Number(
            max_val=200,
            min_val=1,
            is_int=True,
        )
    ),
    field.RestField(
        'collection_timeout',
        required=False,
        encrypted=False,
        default='120',
        validator=validator.Number(
            max_val=3600,
            min_val=10,
            is_int=True,
        )
    ),

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = DataInputModel(
    'unifi_reference',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
