
import ta_emc_isilon_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from account_validation import AccountValidator, IndexValidator
from utils_account import AccountHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='isilon',
        validator=IndexValidator()
    ),
    field.RestField(
        'ip_address',
        required=True,
        encrypted=False,
        default=None,
        validator=AccountValidator()
    ),
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        )
    ),
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_emc_isilon_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AccountHandler,
    )
