import ta_mandiant_digital_threat_monitoring_declare

from mandiant_dtm_validator import ValidateDtmAccount
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'key_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        ),
    ),
    field.RestField(
        'key_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=ValidateDtmAccount(),
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_mandiant_digital_threat_monitoring_account',
    model,
)


if __name__ == '__main__':
  admin_external.handle(
      endpoint,
      handler=ConfigMigrationHandler,
  )
