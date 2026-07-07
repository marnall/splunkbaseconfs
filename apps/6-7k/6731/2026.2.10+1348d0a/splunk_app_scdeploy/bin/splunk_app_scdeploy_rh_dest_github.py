
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
        'help',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'repo',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'secret_name',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'token',
        required=True,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'user',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'limit_role',
        required=True,
        encrypted=False,
        default='sc_admin',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'splunk_app_scdeploy_dest_github',
    model,
    config_name='dest_github',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
