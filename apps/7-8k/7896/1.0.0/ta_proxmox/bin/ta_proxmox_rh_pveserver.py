
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
        'pve_host',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'pve_port',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'ssl_verify',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_proxmox_pveserver',
    model,
    config_name='pveserver',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
