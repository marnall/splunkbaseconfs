
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
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""", 
            ), 
            validator.Number(
                max_val=86400, 
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
        validator=validator.String(
            max_len=100, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'current_fields',
        required=True,
        encrypted=False,
        default='ModemTemp,GsmRSSI,GsmEcIo,NearbyCells,RetriesRemaining,RxBytes,TxBytes',
        validator=validator.String(
            max_len=1024, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'wan3g_fields',
        required=False,
        encrypted=False,
        default='IMEI,GsmCountry,GsmNetwork,idx,cdt_device.name',
        validator=validator.String(
            max_len=1024, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'nearby_current_fields',
        required=False,
        encrypted=False,
        default='PrimaryScramblingCode,RSCP,EcIoMeasurement',
        validator=validator.String(
            max_len=1024, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'timefilter',
        required=True,
        encrypted=False,
        default='range=now - 6m to now',
        validator=validator.String(
            max_len=512, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'page_size',
        required=True,
        encrypted=False,
        default='500',
        validator=validator.Number(
            max_val=5000, 
            min_val=1, 
            is_int=True, 
        )
    ), 
    field.RestField(
        'device_filter',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=512, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'device_name_filter',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=512, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'name_filter',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=512, 
            min_len=0, 
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
    'statseeker_wan3g',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
