
import ta_crowdstrike_identities_declare

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
        default='3 3 * * *',
        validator=validator.Pattern(
            regex=r"""(?:(?:^[3-9][0-9][0-9]$|^[1-9][0-9][0-9][0-9]\d*$)|(?:^\S+(?: \S+){4}))""",
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1, 
            max_len=80, 
        )
    ), 
    field.RestField(
        'cloud_environment',
        required=True,
        encrypted=False,
        default='us1',
        validator=None
    ), 
    field.RestField(
        'api_credentials',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'domains_to_exclude',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'domains_to_include',
        required=False,
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
    'crowdstrike_identities',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
