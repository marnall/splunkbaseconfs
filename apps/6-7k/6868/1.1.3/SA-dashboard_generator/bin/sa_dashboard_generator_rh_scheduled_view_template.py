
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
                regex=r"""^[0-9|a-z|A-Z][\w\- ,]*$""", 
            ), 
            validator.String(
                max_len=50, 
                min_len=1, 
            )
        )
    )
]

fields = [
    field.RestField(
        'description',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'dashboard_type',
        required=True,
        encrypted=False,
        default='1',
        validator=None
    ), 
    field.RestField(
        'cron_schedule',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'to',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'subject',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'message',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'send_pdf',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'send_png',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'inline_png',
        required=False,
        encrypted=False,
        default='0',
        validator=None
    ), 
    field.RestField(
        'view_link',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'email_params',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'sa_dashboard_generator_scheduled_view_template',
    model,
    config_name='scheduled_view_template',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
