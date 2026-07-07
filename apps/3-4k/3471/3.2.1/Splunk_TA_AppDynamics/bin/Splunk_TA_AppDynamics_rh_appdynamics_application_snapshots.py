
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from Splunk_TA_Appdynamics_BaseRestHandler import BaseRestHandler
import logging

util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    )
]

fields = [
    field.RestField(
        'type',
        required=True,
        encrypted=False,
        default='Snapshots',
        validator=None
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.Number(
            max_val=6000000, 
            min_val=60, 
        )
    ), 
    field.RestField(
        'index',
        required=False,
        encrypted=False,
        default='default',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9][a-zA-Z0-9\\_\\-]*$""", 
            ), 
            validator.String(
                max_len=80, 
                min_len=1, 
            )
        )
    ), 
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'duration',
        required=True,
        encrypted=False,
        default='5',
        validator=validator.Number(
            max_val=60, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'application_list',
        required=False,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'metrics_to_collect',
        required=True,
        encrypted=False,
        default='SLOW~VERY_SLOW~STALL~ERROR~NORMAL',
        validator=None
    ), 
    field.RestField(
        'need_props',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'need_exit_calls',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'first_in_chain',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'archived',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'execution_time_in_milis',
        required=False,
        encrypted=False,
        default='0',
        validator=validator.Number(
            max_val=500001, 
            min_val=0, 
            is_int=True, 
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
    'appdynamics_application_snapshots',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=BaseRestHandler,
    )
