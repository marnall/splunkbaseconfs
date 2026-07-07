
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


fields = [
    field.RestField(
        'support_doc_link',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'support_SDK_link',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""", 
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
        'cloud',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'timestamp_selection',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'severity',
        required=True,
        encrypted=False,
        default='all',
        validator=None
    ), 
    field.RestField(
        'start_date',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=10, 
                min_len=0, 
            ), 
            validator.Pattern(
                regex=r"""^20\d{2}-\d{2}-\d{2}$""", 
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
    'crowdstrike_filevantage_json',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
