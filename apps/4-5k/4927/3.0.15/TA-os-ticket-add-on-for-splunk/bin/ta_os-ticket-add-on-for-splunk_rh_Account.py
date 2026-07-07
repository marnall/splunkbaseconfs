
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
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
        'api_endpoint',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(https?:\/\/)[\w.-]+(:\d+)?(\/.*)?$""", 
        )
    ), 
    field.RestField(
        'host1',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9.-]+$""", 
        )
    ), 
    field.RestField(
        'api1',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'host2',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9.-]+$""", 
        )
    ), 
    field.RestField(
        'api2',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'host3',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9.-]+$""", 
        )
    ), 
    field.RestField(
        'api3',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'host4',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9.-]+$""", 
        )
    ), 
    field.RestField(
        'api4',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'host5',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9.-]+$""", 
        )
    ), 
    field.RestField(
        'api5',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_os-ticket-add-on-for-splunk_account',
    model,
    config_name='Account'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
