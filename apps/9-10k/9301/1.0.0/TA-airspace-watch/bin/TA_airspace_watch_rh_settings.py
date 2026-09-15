
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging

util.remove_http_proxy_env_vars()


fields_receiver = [
    field.RestField(
        'adsb_host',
        required=True,
        encrypted=False,
        default='192.168.0.58',
        validator=validator.String(
            max_len=253, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'adsb_port',
        required=True,
        encrypted=False,
        default='8080',
        validator=validator.Number(
            max_val=65535, 
            min_val=1, 
        )
    ), 
    field.RestField(
        'adsb_path',
        required=True,
        encrypted=False,
        default='/data/aircraft.json',
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'request_timeout',
        required=True,
        encrypted=False,
        default='4',
        validator=validator.Number(
            max_val=60, 
            min_val=1, 
        )
    )
]
model_receiver = RestModel(fields_receiver, name='receiver')


fields_geofence = [
    field.RestField(
        'center_lat',
        required=True,
        encrypted=False,
        default='53.8',
        validator=validator.Number(
            max_val=90, 
            min_val=-90, 
        )
    ), 
    field.RestField(
        'center_lon',
        required=True,
        encrypted=False,
        default='-1.55',
        validator=validator.Number(
            max_val=180, 
            min_val=-180, 
        )
    ), 
    field.RestField(
        'radius_nm',
        required=True,
        encrypted=False,
        default='50',
        validator=validator.Number(
            max_val=500, 
            min_val=1, 
        )
    )
]
model_geofence = RestModel(fields_geofence, name='geofence')


fields_logging = [
    field.RestField(
        'loglevel',
        required=True,
        encrypted=False,
        default='INFO',
        validator=validator.Pattern(
            regex=r"""^DEBUG|INFO|WARNING|ERROR|CRITICAL$""", 
        )
    )
]
model_logging = RestModel(fields_logging, name='logging')


endpoint = MultipleModel(
    'ta_airspace_watch_settings',
    models=[
        model_receiver, 
        model_geofence, 
        model_logging
    ],
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
