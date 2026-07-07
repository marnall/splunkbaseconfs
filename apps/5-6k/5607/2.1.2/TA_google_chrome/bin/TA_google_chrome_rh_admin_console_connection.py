
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
        'domain',
        required=True,
        encrypted=False,
        default='',
        validator=validator.AllOf(
            validator.String(
                max_len=8192, 
                min_len=0, 
            ), 
            validator.Pattern(
                regex=r"""^[A-Za-z0-9.-]+\.[a-zA-Z]{2,}$""", 
            )
        )
    ), 
    field.RestField(
        'customerID',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'admin_email',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$""", 
        )
    ), 
    field.RestField(
        'service_account',
        required=True,
        encrypted=True,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_google_chrome_admin_console_connection',
    model,
    config_name='admin_console_connection'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
