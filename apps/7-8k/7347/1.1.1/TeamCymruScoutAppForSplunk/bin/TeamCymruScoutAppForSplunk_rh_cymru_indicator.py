
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from cymru_helpers.validators import IndicatorValidator
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=IndicatorValidator()
    ), 
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='86400',
        validator=validator.Pattern(
            regex=r"""^\d+$""", 
        )
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
        'api_type',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'indicator_type',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'indicators',
        required=True,
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
    'cymru_indicator',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
