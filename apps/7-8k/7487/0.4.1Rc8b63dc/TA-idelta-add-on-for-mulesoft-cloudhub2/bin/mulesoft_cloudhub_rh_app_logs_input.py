
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


fields = [
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='mulesoft',
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='86400',
        validator=validator.Pattern(
            regex=r"""^(?:-1|\d+(?:\.\d+)?)$""", 
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
        'organisation',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'environment',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'app_logs_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
