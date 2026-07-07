
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from sb_delete_checkpoint_rh import DeleteCheckpointExternalHandler
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^(?:-1|\d+(?:\.\d+)?)$""", 
            ), 
            validator.Number(
                max_val=301, 
                min_val=10, 
            )
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
        'azure_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'sb_license',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'query',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'since_date',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'event_delay',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=5, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'sourcetype',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100, 
            min_len=0, 
        )
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'azure_log_analytics',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=DeleteCheckpointExternalHandler,
    )
