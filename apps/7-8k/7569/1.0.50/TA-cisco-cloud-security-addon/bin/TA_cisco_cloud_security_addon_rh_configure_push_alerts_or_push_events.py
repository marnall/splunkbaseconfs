
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from config_push_events_and_push_alerts import Hec_token
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
                max_len=100, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^\S(.*\S)?$""", 
            )
        )
    )
]

fields = [
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'create_new_index',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'description',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'disabled',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_cisco_cloud_security_addon_configure_push_alerts_or_push_events',
    model,
    config_name='configure_push_alerts_or_push_events',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=Hec_token,
    )
