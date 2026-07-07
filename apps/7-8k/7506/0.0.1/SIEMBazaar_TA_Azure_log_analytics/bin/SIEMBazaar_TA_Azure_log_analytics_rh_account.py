
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


fields = [
    field.RestField(
        'tenant_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=50, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'workspace_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=50, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=50, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=50, 
            min_len=1, 
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'siembazaar_ta_azure_log_analytics_account',
    model,
    config_name='account'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
