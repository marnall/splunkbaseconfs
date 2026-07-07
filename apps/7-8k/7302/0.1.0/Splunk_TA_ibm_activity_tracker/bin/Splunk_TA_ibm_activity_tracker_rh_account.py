
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
        'endpoint_url',
        required=True,
        encrypted=False,
        default='https://s3.us-south.cloud-object-storage.appdomain.cloud',
        validator=validator.Pattern(
            regex=r"""^https?://s3(?:\.direct)?(?:\.private)?(?:\.[a-z\-]+)?\.cloud-object-storage\.appdomain\.cloud$""", 
        )
    ), 
    field.RestField(
        'access_key_id',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'secret_access_key',
        required=True,
        encrypted=True,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'splunk_ta_ibm_activity_tracker_account',
    model,
    config_name='account'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
