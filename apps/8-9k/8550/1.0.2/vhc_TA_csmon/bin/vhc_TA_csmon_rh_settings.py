
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


fields_settings = [
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='csmon',
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z][a-zA-Z0-9_-]*$""", 
        )
    )
]
model_settings = RestModel(fields_settings, name='settings')


fields_system_settings = [
    field.RestField(
        'sap_systems',
        required=True,
        encrypted=False,
        default='SERVICEDESC="Logon Check"',
        validator=validator.AllOf(
            validator.String(
                max_len=200, 
                min_len=3, 
            ), 
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9_!="'\s\*\.\-\(\)]+$""", 
            )
        )
    ), 
    field.RestField(
        'hana_systems',
        required=True,
        encrypted=False,
        default='SERVICEDESC="All Services Started"',
        validator=validator.AllOf(
            validator.String(
                max_len=200, 
                min_len=3, 
            ), 
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9_!="'\s\*\.\-\(\)]+$""", 
            )
        )
    )
]
model_system_settings = RestModel(fields_system_settings, name='system_settings')


fields_modus_settings = [
    field.RestField(
        'test_mode',
        required=False,
        encrypted=False,
        default=1,
        validator=None
    )
]
model_modus_settings = RestModel(fields_modus_settings, name='modus_settings')


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
    'vhc_ta_csmon_settings',
    models=[
        model_settings, 
        model_system_settings, 
        model_modus_settings, 
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
