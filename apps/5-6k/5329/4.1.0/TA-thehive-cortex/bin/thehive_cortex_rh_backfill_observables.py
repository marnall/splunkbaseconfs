
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
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z]\w*$""", 
        )
    )
]

fields = [
    field.RestField(
        'interval',
        required=False,
        encrypted=False,
        default='-1',
        validator=validator.Number(
            max_val=-1, 
            min_val=-1, 
        )
    ), 
    field.RestField(
        'index',
        required=False,
        encrypted=False,
        default='default',
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'instance_id',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'backfill_start',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\d{4}-\d{2}-\d{2}(((T| )\d{2}:\d{2}:\d{2})?)$""", 
        )
    ), 
    field.RestField(
        'backfill_end',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\d{4}-\d{2}-\d{2}(((T| )\d{2}:\d{2}:\d{2})?)$""", 
        )
    ), 
    field.RestField(
        'date',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'max_size_value',
        required=False,
        encrypted=False,
        default='1000',
        validator=validator.Number(
            max_val=1000000, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'event_mode',
        required=True,
        encrypted=False,
        default='detailed',
        validator=validator.String(
            max_len=20, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'fields_removal',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=1000, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'extra_data',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=500, 
            min_len=0, 
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
    'backfill_observables',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
