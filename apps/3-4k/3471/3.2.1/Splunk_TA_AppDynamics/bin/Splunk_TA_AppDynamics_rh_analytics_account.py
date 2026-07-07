
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from Splunk_TA_Appdynamics_Analytics_Validator import CustomRestHandler
import logging


util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=250, 
            min_len=1, 
        )
    )
]

fields = [
    field.RestField(
        'appd_analytics_account_name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=250, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'appd_analytics_endpoint',
        required=True,
        encrypted=False,
        default='https://analytics.api.appdynamics.com',
        validator=None
    ), 
    field.RestField(
        'appd_onprem_analytics_url',
        required=False,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^(?:(?:https?|ftp|opc\.tcp):\/\/)?(?:\S+(?::\S*)?@)?(?:(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z\u00a1-\uffff0-9]+-?_?)*[a-z\u00a1-\uffff0-9]+)(?:\.(?:[a-z\u00a1-\uffff0-9]+-?)*[a-z\u00a1-\uffff0-9]+)*(?:\.(?:[a-z\u00a1-\uffff]{2,}))?)(?::\d{2,5})?(?:\/[^\s]*)?$""", 
        )
    ), 
    field.RestField(
        'appd_analytics_secret',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'splunk_ta_appdynamics_analytics_account',
    model,
    config_name='analytics_account',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CustomRestHandler,
    )
