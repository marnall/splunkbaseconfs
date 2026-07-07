
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
        'misp_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^https://[0-9a-zA-Z\-\.]+(?:\:\d+)?""", 
        )
    ), 
    field.RestField(
        'misp_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'misp_verifycert',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'misp_ca_full_path',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'misp_use_proxy',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'client_use_cert',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'client_cert_full_path',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'prefix',
        required=True,
        encrypted=False,
        default='misp_',
        validator=validator.AllOf(
            validator.String(
                max_len=10, 
                min_len=2, 
            ), 
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w+$""", 
            )
        )
    ), 
    field.RestField(
        'connection_timeout',
        required=True,
        encrypted=False,
        default=3,
        validator=validator.Number(
            max_val=300, 
            min_val=1, 
            is_int=True, 
        )
    ), 
    field.RestField(
        'read_timeout',
        required=True,
        encrypted=False,
        default=200,
        validator=validator.Number(
            max_val=600, 
            min_val=1, 
            is_int=True, 
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'misp42splunk_instances',
    model,
    config_name='instances',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
