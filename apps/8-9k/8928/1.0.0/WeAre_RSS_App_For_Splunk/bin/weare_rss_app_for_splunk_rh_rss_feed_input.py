
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
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
        'url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^https?://.+""", 
            ), 
            validator.String(
                max_len=2048, 
                min_len=1, 
            )
        )
    ), 
    field.RestField(
        'verify_ssl',
        required=False,
        encrypted=False,
        default=1,
        validator=None
    ), 
    field.RestField(
        'http_timeout',
        required=True,
        encrypted=False,
        default='30',
        validator=validator.Number(
            max_val=300, 
            min_val=1, 
            is_int=True, 
        )
    ), 
    field.RestField(
        'index',
        required=False,
        encrypted=False,
        default='default',
        validator=validator.IndexName()
    ), 
    field.RestField(
        'sourcetype',
        required=True,
        encrypted=False,
        default='rss:feed',
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'timestamp_mode',
        required=True,
        encrypted=False,
        default='indexing_time',
        validator=None
    ), 
    field.RestField(
        'timestamp_field',
        required=False,
        encrypted=False,
        default='published',
        validator=None
    ), 
    field.RestField(
        'strip_html_tags',
        required=False,
        encrypted=False,
        default=0,
        validator=None
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""", 
            ), 
            validator.Number(
                max_val=86400, 
                min_val=10, 
            )
        )
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None, special_fields=special_fields)



endpoint = DataInputModel(
    'rss_feed_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
