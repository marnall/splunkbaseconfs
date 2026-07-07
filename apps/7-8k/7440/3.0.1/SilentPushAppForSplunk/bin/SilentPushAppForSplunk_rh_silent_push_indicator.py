
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from silent_push_helpers.validators import IndicatorValidator, ThreatIntelligenceTypeValidator
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
        default=86400,
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
        'threat_intelligence_type',
        required=True,
        encrypted=False,
        default=None,
        validator=ThreatIntelligenceTypeValidator()
    ),
    field.RestField(
        'silent_push_feed_uuid',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'silent_push_filter_profile',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'data_export_url',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'feed_scanner_url',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'iofa_exports_url',
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
    'silent_push_indicator',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
