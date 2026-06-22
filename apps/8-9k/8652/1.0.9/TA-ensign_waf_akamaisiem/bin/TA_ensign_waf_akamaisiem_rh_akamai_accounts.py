
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
                regex=r"""^[a-zA-Z0-9_\\-]+$""", 
            )
        )
    )
]

fields = [
    field.RestField(
        'account_enabled',
        required=False,
        encrypted=False,
        default=1,
        validator=None
    ), 
    field.RestField(
        'akamai_host',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9._-]+$""", 
        )
    ), 
    field.RestField(
        'client_token',
        required=True,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'access_token',
        required=True,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'disable_ssl',
        required=False,
        encrypted=False,
        default=0,
        validator=None
    ), 
    field.RestField(
        'cert_location',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=4096, 
            min_len=0, 
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_ensign_waf_akamaisiem_akamai_accounts',
    model,
    config_name='akamai_accounts',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
