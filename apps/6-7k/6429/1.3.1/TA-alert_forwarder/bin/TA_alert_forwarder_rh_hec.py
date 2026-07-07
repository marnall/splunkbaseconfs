
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
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
            validator.String(
                max_len=50, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""", 
            )
        )
    )
]

fields = [
    field.RestField(
        'hostname',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'port',
        required=True,
        encrypted=False,
        default='8088',
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'verify',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'token',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'retry_count',
        required=True,
        encrypted=False,
        default='3',
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'sleep_interval',
        required=True,
        encrypted=False,
        default='60',
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'timeout',
        required=True,
        encrypted=False,
        default='30',
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_alert_forwarder_hec',
    model,
    config_name='hec',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
