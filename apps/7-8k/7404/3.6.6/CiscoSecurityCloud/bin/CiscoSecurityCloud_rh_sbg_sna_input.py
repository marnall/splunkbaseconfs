
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
        'ip_address',
        required=True,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^(?=.{1,253}$)(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+(?!-)[A-Za-z0-9-]{2,63}$""", 
        )
    ), 
    field.RestField(
        'domain_id',
        required=True,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^[1-9]\d*$""", 
        )
    ), 
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'password',
        required=False,
        encrypted=True,
        default='',
        validator=None
    ), 
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    ), 
    field.RestField(
        'alarms',
        required=False,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'include_risk_events',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.Number(
            max_val=900, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'sourcetype',
        required=False,
        encrypted=False,
        default='cisco:sna',
        validator=None
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='cisco_sna',
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
    'sbg_sna_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
