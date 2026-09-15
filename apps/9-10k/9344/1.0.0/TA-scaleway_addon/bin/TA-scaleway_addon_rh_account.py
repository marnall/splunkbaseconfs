
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
        'description',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'organization_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=36, 
                min_len=36, 
            ), 
            validator.Pattern(
                regex=r"""^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$""", 
            )
        )
    ), 
    field.RestField(
        'scw_secret_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=36, 
                min_len=36, 
            ), 
            validator.Pattern(
                regex=r"""^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$""", 
            )
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta-scaleway_addon_account',
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
