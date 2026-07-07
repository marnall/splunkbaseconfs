
import ta_bloodhound_enterprise_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from TA_bloodhound_enterprise_account_validation import ValidateAccount

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'domain_name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?$""",
        )
    ),
    field.RestField(
        'token_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z0-9]{8}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{12}$""",
        )
    ),  
    field.RestField(
        'token_key',
        required=True,
        encrypted=True,
        default=None,
        validator=ValidateAccount()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_bloodhound_enterprise_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
