
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_ta_talos_intelligence.custom_certificate_rest_handler import CustomRestHandlerTalosCertificate
import logging


util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default='Talos_Intelligence_Service',
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
        'service_account',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.Pattern(
            regex=r"""^-----BEGIN CERTIFICATE-----\r?\n([a-zA-Z0-9+/]{64}\r?\n)*([a-zA-Z0-9+/]{1,63}=?=?\r?\n)?-----END CERTIFICATE-----\r?\n-----BEGIN RSA PRIVATE KEY-----\r?\n([a-zA-Z0-9+/]{64}\r?\n)*([a-zA-Z0-9+/]{1,63}=?=?\r?\n)?-----END RSA PRIVATE KEY-----(\r?\n)?$""", 
        )
    ), 
    field.RestField(
        'fingerprint',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'splunk_ta_talos_intelligence_account',
    model,
    config_name='account',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CustomRestHandlerTalosCertificate,
    )
