# encoding = utf-8

""" The only change TruSTAR made to this file is it changed the
"interval" field from "required = True" to "required = False" b/c
we removed that field from the modinput config page in
"globalConfig.json".  """

import trustar_unified_declare

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
        required=False,                 # <----- we changed this from "True" to "False".
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""", 
        )
    ), 
    field.RestField(
        'index',                       # <---- FYI: "index" programmatic fieldname is associated
        required=True,                 #       with the "kvstore group" setting.
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1, 
            max_len=80, 
        )
    ), 
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'enclave_ids',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'ioc_types',
        required=True,
        encrypted=False,
        default='IP~EMAIL_ADDRESS~MD5~SHA1~SHA256~SOFTWARE~REGISTRY_KEY~URL~DOMAIN',
        validator=None
    ), 
    field.RestField(
        'tags',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'expiration_days',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)

endpoint = DataInputModel(
    'trustar_observables_to_kvstores',
    model,
)

if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
