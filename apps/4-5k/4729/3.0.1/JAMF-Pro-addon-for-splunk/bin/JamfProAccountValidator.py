
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from jamf_pro_addon_for_splunk_account_validation import AdminExternalHandler
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
        'jss_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^https?://[^\s/$.?#].[^\s]*$""", 
            ), 
            validator.String(
                max_len=4096, 
                min_len=1, 
            )
        )
    ), 
    field.RestField(
        'auth_type',
        required=True,
        encrypted=False,
        default='api_client',
        validator=None
    ), 
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'test_credentials',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'permissions_info',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'jamf_pro_addon_for_splunk_account',
    model,
    config_name='account'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
