
import ta_wiz_addon_for_splunk_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util

util.remove_http_proxy_env_vars()

WIZ_REGEX = "((http|https)://)[\w.]+(.wiz.(io|us))[/\w]+"

fields = [
    field.RestField(
        'api_server_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=WIZ_REGEX,
        )
    ), 
    field.RestField(
        'jwt_generation_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=WIZ_REGEX,
        )
    ), 
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=8,
            max_len=8192, 
        )
    ), 
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=8,
            max_len=8192, 
        )
    ) 
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_wiz_addon_for_splunk_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(endpoint)
