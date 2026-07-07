
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from lv_rh import lV
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'licensekey',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'license_proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'example_help_link',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'siembazaar_ta_dynatrace_audit_logs_license',
    model,
    config_name='license'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=lV,
    )
