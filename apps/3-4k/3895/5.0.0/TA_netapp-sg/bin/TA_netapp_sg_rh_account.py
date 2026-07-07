# Copyright (c) 2022 NetApp, Inc., All Rights Reserved

import ta_netapp_sg_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from TA_netapp_sg_account_validation import ValidateAccount
util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'auth_type',
        required=True,
        encrypted=False,
        default='basic',
        validator=None
    ), 
    field.RestField(
        'account_ip',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default='',
        validator=ValidateAccount()
    ), 
    field.RestField(
        'confirm_password',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    )
]
model_account = RestModel(fields, name='account')

endpoint = SingleModel(
    'ta_netapp_sg_account',
    model_account
)

if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
