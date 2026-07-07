
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
        'cloud',
        required=True,
        encrypted=False,
        default='us_commercial',
        validator=None
    ), 
    field.RestField(
        'account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'platform',
        required=True,
        encrypted=False,
        default='all',
        validator=None
    ), 
    field.RestField(
        'timestamp',
        required=False,
        encrypted=False,
        default='modified_timestamp',
        validator=None
    ), 
    field.RestField(
        'start_date',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(\d{4}-\d{2}-\d{2})?$""", 
        )
    ), 
    field.RestField(
        'online_only',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'crowdstrike_device_json',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
