
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


fields_advanced_configuration = [
    field.RestField(
        'blocklist_risk_object_patterns',
        required=False,
        encrypted=False,
        default='"unknown","N/A","-"',
        validator=None
    ), 
    field.RestField(
        'blocklist_threat_object_patterns',
        required=False,
        encrypted=False,
        default='"unknown","N/A","-"',
        validator=None
    )
]
model_advanced_configuration = RestModel(fields_advanced_configuration, name='advanced_configuration')


endpoint = MultipleModel(
    'ta_risk_superhandler_settings',
    models=[
        model_logging, 
        model_advanced_configuration
    ],
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
