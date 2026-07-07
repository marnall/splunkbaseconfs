
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
        validator=None
    )
]

fields = [
    field.RestField(
        'base_url',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'port',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'hec_token',
        required=True,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'fields_to_include',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_send_to_hec_command_target',
    model,
    config_name='target',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
