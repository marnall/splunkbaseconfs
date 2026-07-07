
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from thousandeyes_account_save_delete_rh import CustomAccountHandler
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
                max_len=200, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^[\w\-\+][\w\-\+\.]*@[\w\-\+\.]+$""", 
            )
        )
    )
]

fields = [
    field.RestField(
        'device_code',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'user_code',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'verification_url',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'code',
        required=False,
        encrypted=False,
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
        'refresh_token',
        required=True,
        encrypted=True,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_cisco_thousandeyes_account',
    model,
    config_name='account',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CustomAccountHandler,
    )
