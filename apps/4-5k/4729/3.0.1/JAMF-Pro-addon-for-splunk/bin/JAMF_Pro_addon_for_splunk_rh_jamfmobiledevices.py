
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
        default='86400',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""", 
            ), 
            validator.Number(
                max_val=31536000, 
                min_val=900, 
            )
        )
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
        'input_status_control',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'platforms',
        required=False,
        encrypted=False,
        default='iphone,ipad,appletv',
        validator=None
    ), 
    field.RestField(
        'exclude_unmanaged',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'skip_unchanged',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'days_since_contact',
        required=False,
        encrypted=False,
        default='0',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'sections',
        required=False,
        encrypted=False,
        default='security,general,location,groupMemberships,purchasing,applications',
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
    'jamfmobiledevices',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
