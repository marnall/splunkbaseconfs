
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from Splunk_TA_Appdynamics_Custom_Data_Validator import CustomRestHandler
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
        default='Custom',
        validator=None
    ), 
    field.RestField(
        'source_type_entry',
        required=True,
        encrypted=False,
        default='appdynamics_custom_data',
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'source_entry',
        required=True,
        encrypted=False,
        default='appdynamics_custom_metric',
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=300,
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
        required=True,
        encrypted=False,
        default='',
        validator=None
    ), 
    field.RestField(
        'metrics_to_collect',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=10240, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'collect_baselines_radio',
        required=False,
        encrypted=False,
        default='default',
        validator=None
    ), 
    field.RestField(
        'compress_data_flag',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None, special_fields=special_fields)



endpoint = DataInputModel(
    'appdynamics_custom_metrics',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CustomRestHandler,
    )
