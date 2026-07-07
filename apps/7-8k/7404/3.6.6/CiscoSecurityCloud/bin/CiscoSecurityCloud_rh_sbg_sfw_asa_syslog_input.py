
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
        default='',
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
        'type',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'port',
        required=True,
        encrypted=False,
        default='514',
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'restrictToHost',
        required=False,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'sourcetype',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'event_types',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='cisco_sfw_ftd_syslog',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='600',
        validator=validator.Number(
            max_val=900, 
            min_val=1, 
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
    'sbg_sfw_asa_syslog_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
