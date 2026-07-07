
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from thousandeyes_test_metrics_stream_edit_delete_rh import StreamInputHandler
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
        'thousandeyes_user',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'thousandeyes_acc_group',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'tags',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'cea_tests',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'endpoint_tests',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'hec_target',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^https?:\/\/(localhost|(\d{1,3}\.){3}\d{1,3}|[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*)(:\d{1,5})?(\/.*)?$""", 
        )
    ), 
    field.RestField(
        'hec_token',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'hec_link',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'test_index',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'thousandeyes_stream_id',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'related_paths',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'index',
        required=False,
        encrypted=False,
        default='default',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'interval',
        required=False,
        encrypted=False,
        default='300',
        validator=validator.Number(
            max_val=31622400, 
            min_val=180, 
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
    'test_metrics_stream',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=StreamInputHandler,
    )
