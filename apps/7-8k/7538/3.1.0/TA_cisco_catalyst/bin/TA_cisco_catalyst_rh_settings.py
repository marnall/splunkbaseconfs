
import logging

import import_declare_test
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    MultipleModel,
    RestModel,
    field,
    validator,
)

util.remove_http_proxy_env_vars()


fields_logging = [
    field.RestField(
        'loglevel',
        required=True,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
fields_additional_parameters = [
    field.RestField(
        "ca_certs_path",
        required=False,
        encrypted=False,
        default="",
        validator=None,
    ),
    field.RestField(
        "verify_ssl",
        required=False,
        encrypted=False,
        default="",
        validator=None,
    ),
]
fields_additional_settings_parameters = [
    field.RestField(
        "splunk_mgmt_env_type",
        required=True,
        encrypted=False,
        default="local_instance",
        validator=None
    ),
    field.RestField(
        "splunk_mgmt_host",
        required=False,
        encrypted=False,
        default="localhost",
        validator=None
    ),
    field.RestField(
        "splunk_mgmt_port",
        required=False,
        encrypted=False,
        default="8089",
        validator=validator.Number(
            max_val=65535,
            min_val=1,
        )
    ),
    field.RestField(
        "splunk_mgmt_username",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        "splunk_mgmt_password",
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    )
]
model_logging = RestModel(fields_logging, name='logging')
model_additional_parameters = RestModel(
    fields_additional_parameters, name="additional_parameters"
)
model_additional_settings_parameters = RestModel(
    fields_additional_settings_parameters, name="additional_settings_parameters"
)

endpoint = MultipleModel(
    'ta_cisco_catalyst_settings',
    models=[
        model_logging,
        model_additional_parameters,
        model_additional_settings_parameters
    ],
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
