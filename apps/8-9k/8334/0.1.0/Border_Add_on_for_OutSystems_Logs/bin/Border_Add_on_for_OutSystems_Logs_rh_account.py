
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
                max_len=100, 
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
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=500, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'base_api_url',
        required=True,
        encrypted=False,
        default='https://server.com/MonitorProbe/rest/PlatformLogs',
        validator=validator.AllOf(
            validator.String(
                max_len=500, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^https?://""", 
            )
        )
    ), 
    field.RestField(
        'environment',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'verify_ssl',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'border_add_on_for_outsystems_logs_account',
    model,
    config_name='account',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
