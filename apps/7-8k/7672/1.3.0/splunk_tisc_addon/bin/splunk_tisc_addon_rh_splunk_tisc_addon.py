
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from tisc_rest_handler import TISCRestHandler
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
        'interval',
        required=True,
        encrypted=False,
        default=120,
        validator=validator.Number(
            max_val=65535, 
            min_val=60, 
            is_int=True, 
        )
    ), 
    field.RestField(
        'days_till_expiry',
        required=False,
        encrypted=False,
        default=30,
        validator=validator.Number(
            max_val=65535, 
            min_val=0, 
            is_int=True, 
        )
    ), 
    field.RestField(
        'never_expire',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'additional_attributes',
        required=False,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'filters',
        required=False,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'json_filters',
        required=False,
        encrypted=False,
        default='{"boolean_operator":"AND","filters":[{"field_name":"reputation","operator":"IN","field_value":"clean,suspicious,malicious"},{"field_name":"threat_score","operator":">","field_value":"90"},{"field_name":"confidence","operator":">","field_value":"90"},{"field_name":"type","operator":"=","field_value":"ip_v4_address"}]}',
        validator=None
    ), 
    field.RestField(
        'advanced',
        required=False,
        encrypted=False,
        default=0,
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
    'splunk_tisc_addon',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=TISCRestHandler,
    )
