
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
        'support_doc_link',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'support_SDK_link',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=32, 
            min_len=32, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=40, 
            min_len=40, 
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_crowdstrike_falcon_filevantage_account',
    model,
    config_name='account'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
