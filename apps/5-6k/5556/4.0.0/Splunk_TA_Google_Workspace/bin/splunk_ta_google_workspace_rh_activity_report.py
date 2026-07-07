
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from gws_delete_checkpoint_rh import GwsDeleteCheckpointExternalHandler
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
        'application',
        required=True,
        encrypted=False,
        default='admin',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""", 
            ), 
            validator.Number(
                max_val=3600, 
                min_val=20, 
            )
        )
    ), 
    field.RestField(
        'lookbackOffset',
        required=True,
        encrypted=False,
        default='1800',
        validator=validator.Number(
            max_val=216000, 
            min_val=60, 
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
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
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
    'activity_report',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=GwsDeleteCheckpointExternalHandler,
    )
