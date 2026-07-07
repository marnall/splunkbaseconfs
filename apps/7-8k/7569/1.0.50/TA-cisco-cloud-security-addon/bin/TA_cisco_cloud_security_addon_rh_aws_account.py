
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from aws_accounts_validator_rh import AWSAccountsValidator
import logging


util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""", 
            ), 
            validator.String(
                max_len=100, 
                min_len=1, 
            )
        )
    )
]

fields = [
    field.RestField(
        'access_key_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}""", 
        )
    ), 
    field.RestField(
        'secret_access_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.Pattern(
            regex=r"""[A-Za-z0-9/+=]{40}""", 
        )
    ), 
    field.RestField(
        'region',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-z0-9-]+-\d{1,2}$""", 
        )
    ), 
    field.RestField(
        'secure_access_client_id',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'secure_access_client_secret',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    ), 
    field.RestField(
        'auto_rotate_key',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'input_names',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_cisco_cloud_security_addon_aws_account',
    model,
    config_name='aws_account',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AWSAccountsValidator,
    )
