import app_qintel_qsentry_feed_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()

fields_qsentry_feed = [
    field.RestField(
        'qsentry_api_url',
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'qsentry_days',
        required=False,
        encrypted=False,
        default='1',
        validator=None
    ),
    field.RestField(
        'feed_age',
        required=False,
        encrypted=False,
        default='2',
        validator=None
    ),
]

fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]

model_qsentry_feed = RestModel(fields_qsentry_feed, name='qsentry_feed')
model_logging = RestModel(fields_logging, name='logging')


endpoint = MultipleModel(
    'qintel_qsentry_feed_settings',
    models=[
        model_qsentry_feed,
        model_logging,
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
