
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
        'interval',
        required=False,
        encrypted=False,
        default=900,
        validator=validator.Number(
            max_val=31536000, 
            min_val=0, 
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
        'user_lat_long',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^([0-9\.]+\,[0-9\.\-]+)$""", 
        )
    ), 
    field.RestField(
        'northwest_lat_long',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^([0-9\.\-]+\,[0-9\.\-]+)$""", 
        )
    ), 
    field.RestField(
        'southeast_lat_long',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^([0-9\.\-]+\,[0-9\.\-]+)$""", 
        )
    ), 
    field.RestField(
        'help_link',
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
    'tesla_collect_tp_suc_data',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
