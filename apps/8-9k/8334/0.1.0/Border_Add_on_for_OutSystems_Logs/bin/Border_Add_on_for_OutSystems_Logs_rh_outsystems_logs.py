
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from outsystems_logs_delete_rh import OutSystemsLogsDeleteHandler
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
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.Number(
            max_val=31536000, 
            min_val=60, 
        )
    ), 
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
        'account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'endpoint',
        required=True,
        encrypted=False,
        default='Integrations',
        validator=None
    ), 
    field.RestField(
        'event_delay',
        required=False,
        encrypted=False,
        default='15',
        validator=validator.Number(
            max_val=1440, 
            min_val=0, 
        )
    ), 
    field.RestField(
        'date_offset_hours',
        required=False,
        encrypted=False,
        default='3',
        validator=validator.Number(
            max_val=8760, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'fetch_chunk_minutes',
        required=False,
        encrypted=False,
        default='5',
        validator=validator.Number(
            max_val=1440, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'sleep_time_ms',
        required=False,
        encrypted=False,
        default='1000',
        validator=validator.Number(
            max_val=60000, 
            min_val=0, 
        )
    ), 
    field.RestField(
        'start_time',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z)?$""", 
        )
    ), 
    field.RestField(
        'end_time',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z)?$""", 
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
    'outsystems_logs',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=OutSystemsLogsDeleteHandler,
    )
