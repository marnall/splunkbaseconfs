
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from geoip_handler import GeoipDatabasesHandler
import logging


util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[A-Za-z0-9-]+$""", 
        )
    )
]

fields = [

]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'geoip_databases',
    model,
    config_name='databases',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=GeoipDatabasesHandler,
    )
