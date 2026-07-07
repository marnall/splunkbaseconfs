
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
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""", 
            ), 
            validator.Number(
                max_val=86401, 
                min_val=10, 
            )
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
        'ipf_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^https://[A-Za-z0-9._-]+(:[0-9]{1,5})?(/.*)?$""", 
            ), 
            validator.String(
                max_len=8192, 
                min_len=1, 
            )
        )
    ), 
    field.RestField(
        'snapshot_id',
        required=False,
        encrypted=False,
        default='$last',
        validator=None
    ), 
    field.RestField(
        'use_ipf_timestamp',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'load_intent_checks',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'only_count',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'table_path',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'table_filter',
        required=False,
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
model = RestModel(fields, name=None, special_fields=special_fields)



endpoint = DataInputModel(
    'ipf_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
