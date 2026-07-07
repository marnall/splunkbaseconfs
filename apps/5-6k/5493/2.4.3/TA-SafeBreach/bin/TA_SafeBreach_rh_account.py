
import ta_safebreach_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from TA_SafeBreach_account_validation import ValidateAccount
util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'host_name',
        required=True,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"^(?![hH][tT]{2}[pP][sS]?[:/]).*"
        )
    ),
    field.RestField(
        'account_id',
        required=True,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""",
        )
    ),
    field.RestField(
        'api_token',
        required=True,
        encrypted=True,
        default='',
        validator=ValidateAccount()
    ),
    field.RestField(
        'verify_ssl',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_safebreach_account',
    model,
)

if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
