
import ta_puppet_alert_actions_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=200, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'pe_token',
        required=False,
        encrypted=False,
        default=0,
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_puppet_alert_actions_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
    )
