
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
from TA_GoogleSCC_input_validation import CredsValidator

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^\-[1-9]\d*$|^\d*$""", 
            ), 
            validator.Number(
                max_val=900, 
                min_val=300, 
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
        'google_scc_account',
        required=True,
        encrypted=False,
        default=None,
        validator=CredsValidator()
    ), 
    field.RestField(
        'audit_logs_subscription_id',
        required=True,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^projects/[^/]+/subscriptions/[^/]+$"""
        )
    ), 
    field.RestField(
        'maximum_fetching',
        required=True,
        encrypted=False,
        default='500',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^\-[1-9]\d*$|^\d*$""", 
            ), 
            validator.Number(
                max_val=5000, 
                min_val=500, 
            )
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
    'auditlog_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
