
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from scaleway_audittrail_custom_handler_rh import ScalewayCustomHandler
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
        'endpoint',
        required=False,
        encrypted=False,
        default='/audit-trail/v1alpha1/regions/{region}/events',
        validator=None
    ), 
    field.RestField(
        'sourcetype',
        required=False,
        encrypted=False,
        default='scaleway:audittrail_events',
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
                max_val=604800, 
                min_val=60, 
            )
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
        'account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'start_date',
        required=False,
        encrypted=False,
        default='2026-01-01',
        validator=None
    ), 
    field.RestField(
        'region',
        required=True,
        encrypted=False,
        default='fr-par',
        validator=None
    ), 
    field.RestField(
        'project_id',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=36, 
                min_len=36, 
            ), 
            validator.Pattern(
                regex=r"""^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$""", 
            )
        )
    ), 
    field.RestField(
        'product_name',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=100, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^[\w-]*$""", 
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
    'audittrail_events',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=ScalewayCustomHandler,
    )
