import ta_mandiant_digital_threat_monitoring_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""",
        ),
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1,
            max_len=80,
        ),
    ),
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        'minimum_m_score',
        required=True,
        encrypted=False,
        default='80',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        'alert_status',
        required=True,
        encrypted=False,
        default='*',
        validator=None,
    ),
    field.RestField(
        'alert_types',
        required=True,
        encrypted=False,
        default='*',
        validator=None,
    ),
    field.RestField('disabled', required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    'dtm_alerts',
    model,
)


if __name__ == '__main__':
  admin_external.handle(
      endpoint,
      handler=ConfigMigrationHandler,
  )
