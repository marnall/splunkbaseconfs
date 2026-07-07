
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
        'etd_api_key',
        required=False,
        encrypted=True,
        default='',
        validator=None
    ), 
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'client_secret',
        required=False,
        encrypted=True,
        default='',
        validator=None
    ), 
    field.RestField(
        'etd_region',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'etd_log_types',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'etd_import_time_range',
        required=True,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ), 
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=4096, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default='',
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=50, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'proxy_rdns',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='3600',
        validator=validator.Number(
            max_val=10800, 
            min_val=3600, 
        )
    ), 
    field.RestField(
        'sourcetype',
        required=False,
        encrypted=False,
        default='cisco:etd',
        validator=None
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='cisco_etd',
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
    'sbg_etd_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
