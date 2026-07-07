
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
        'serial_no',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9]*$""", 
            ), 
            validator.String(
                max_len=10, 
                min_len=10, 
            )
        )
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^(?:-1|\d+(?:\.\d+)?)$""", 
            ), 
            validator.Number(
                max_val=301, 
                min_val=10, 
            )
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='givenergy',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-z0-9][a-z0-9_-]*$""", 
            ), 
            validator.String(
                max_len=100, 
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
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'get_readings',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
