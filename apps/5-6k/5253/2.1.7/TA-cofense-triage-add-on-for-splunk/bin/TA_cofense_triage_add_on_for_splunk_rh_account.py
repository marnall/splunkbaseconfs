
import ta_cofense_triage_add_on_for_splunk_declare
from cofense_triage_validators import ValidateCofenseInstance

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
        'client_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'host_url',
        required=True,
        encrypted=False,
        default=None,
        validator=ValidateCofenseInstance()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_cofense_triage_add_on_for_splunk_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
