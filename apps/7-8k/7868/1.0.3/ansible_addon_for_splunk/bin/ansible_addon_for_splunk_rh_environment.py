
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
        'integration_type',
        required=True,
        encrypted=False,
        default='webhook',
        validator=None
    ), 
    field.RestField(
        'environment',
        required=False,
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
    ), 
    field.RestField(
        'bootstrap_servers',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=8192, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^[\w.\-]+(:\d+)?(,[\w.\-]+(:\d+)?)*$""", 
            )
        )
    ), 
    field.RestField(
        'security_protocol',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=50, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'sasl_plain_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'sasl_plain_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'webhook_endpoint',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(https:\/\/)(?:\S+(?::\S*)?@)?(?:(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|localhost|(?:(?:[a-z\u00a1-\uffff0-9]+-?_?)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,})))?(?::([1-9]\d{0,3}|[1-5]\d{4}|6[0-4]\d{3}|65[0-4]\d{2}|655[0-2]\d|6553[0-5]))?(?:\/[^\s]*)?$""", 
        )
    ), 
    field.RestField(
        'ssl_check_hostname',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'auth_type',
        required=False,
        encrypted=False,
        default='none',
        validator=validator.String(
            max_len=50, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'basic_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'basic_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'token',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'connection_timeout',
        required=False,
        encrypted=False,
        default=10,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[1-9]\d*$""", 
            ), 
            validator.Number(
                max_val=600, 
                min_val=1, 
            )
        )
    ), 
    field.RestField(
        'retries',
        required=False,
        encrypted=False,
        default=3,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^\d+$""", 
            ), 
            validator.Number(
                max_val=10, 
                min_val=0, 
            )
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ansible_addon_for_splunk_environment',
    model,
    config_name='environment',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
