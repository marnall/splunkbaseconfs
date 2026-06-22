
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
        'endpoint',
        required=True,
        encrypted=False,
        default='webexapis.com',
        validator=None
    ), 
    field.RestField(
        'is_gov_account',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'gov_api_reference_link',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'client_id',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'client_secret',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'redirect_url',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'scope',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'access_token',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'refresh_token',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'instance_url',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_cisco_webex_add_on_for_splunk_account',
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
