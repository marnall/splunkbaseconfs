
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
                regex=r"""^[a-zA-Z0-9_\-]*$""", 
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
        'interval',
        required=True,
        encrypted=False,
        default='60',
        validator=validator.Pattern(
            regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""", 
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='main',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'akamai_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'config_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[0-9]+$""", 
        )
    ), 
    field.RestField(
        'limit_num',
        required=False,
        encrypted=False,
        default='600000',
        validator=validator.Pattern(
            regex=r"""^[0-9]+$""", 
        )
    ), 
    field.RestField(
        'proxy_server',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'custom_sourcetype',
        required=False,
        encrypted=False,
        default='ensign_akamaisiem',
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9_:\-\.]*$""", 
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
    'akamai_siem_source',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
