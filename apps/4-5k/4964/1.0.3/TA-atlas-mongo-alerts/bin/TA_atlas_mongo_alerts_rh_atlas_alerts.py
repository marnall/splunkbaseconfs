
import ta_atlas_mongo_alerts_declare

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
        default=None,
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""", 
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'atlasBaseUrl',
        required=True,
        encrypted=False,
        default='https://cloud.mongodb.com/api/atlas/v1.0',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'apiPublicKey',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'apiPrivateKey',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'onlyLastXMin',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'sinceMinutesAgo',
        required=False,
        encrypted=False,
        default='150',
        validator=validator.String(
            max_len=8192, 
            min_len=0, 
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
    'atlas_alerts',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
