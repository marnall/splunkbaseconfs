
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from cisco_cloud_security_addon_rh import ModInputRestHandler
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
        default=600,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""", 
            ), 
            validator.Number(
                max_val=100000, 
                min_val=60, 
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
        'region',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'access_key_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=256, 
            min_len=16, 
        )
    ), 
    field.RestField(
        'secret_access_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=256, 
            min_len=16, 
        )
    ), 
    field.RestField(
        'bucket_name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'prefix',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'start_date',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(20[0-9]{2})(-)(0[1-9]|1[0-2])(-)(0[1-9]|1[0-9]|2[0-9]|3[0,1])$""", 
        )
    ), 
    field.RestField(
        'event_type',
        required=True,
        encrypted=False,
        default='dns',
        validator=None
    ), 
    field.RestField(
        'account_name',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'event_log_name',
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
    'cisco_cloud_security_addon',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=ModInputRestHandler,
    )
