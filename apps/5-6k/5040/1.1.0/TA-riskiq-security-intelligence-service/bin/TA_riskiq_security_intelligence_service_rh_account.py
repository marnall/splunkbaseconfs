"""Rh File for the Account."""

import ta_riskiq_security_intelligence_service_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from riskiqsis_account_validation import AccessKeyValidator
from riskiqsis_account_utils import AccountHandler, AccountModel

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        'accesskey',
        required=True,
        encrypted=False,
        default=None,
        validator=AccessKeyValidator()
    ),
    field.RestField(
        'secretkey',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'data_types',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = AccountModel(
    'ta_riskiq_security_intelligence_service_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AccountHandler,
    )
