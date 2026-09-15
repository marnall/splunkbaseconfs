
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from posthog_account_handler import PostHogAccountHandler
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
                max_len=50, 
                min_len=1, 
            )
        )
    )
]

fields = [
    field.RestField(
        'posthog_host',
        required=True,
        encrypted=False,
        default='https://us.posthog.com',
        validator=validator.Pattern(
            regex=r"""^https://[A-Za-z0-9.-]+(:[0-9]{1,5})?$""", 
        )
    ), 
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^phx_[A-Za-z0-9]+$""", 
            ), 
            validator.String(
                max_len=200, 
                min_len=1, 
            )
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_posthog_activity_logs_account',
    model,
    config_name='account',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=PostHogAccountHandler,
    )
