
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
        'api_key',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'org_id',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'start_date',
        required=False,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^$|^\d{4}-\d{2}-\d{2}""", 
        )
    ), 
    field.RestField(
        'end_date',
        required=False,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^$|^\d{4}-\d{2}-\d{2}""", 
        )
    ), 
    field.RestField(
        'use_existing_checkpoint',
        required=False,
        encrypted=False,
        default='yes',
        validator=None
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""", 
            ), 
            validator.Number(
                max_val=31536000, 
                min_val=1, 
            )
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.AllOf(
            validator.String(
                max_len=80, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9][a-zA-Z0-9\_\-]*$""", 
            )
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
    'bitbucket_audit_log',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
