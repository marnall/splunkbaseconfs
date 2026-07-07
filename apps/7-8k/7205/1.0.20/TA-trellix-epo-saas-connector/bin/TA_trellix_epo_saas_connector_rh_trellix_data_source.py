
import ta_trellix_epo_saas_connector_declare

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
            min_len=1, 
            max_len=80, 
        )
    ),
    field.RestField(
        'audit_source',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'iam_url',
        required=True,
        encrypted=False,
        default='https://iam.cloud.trellix.com',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'api_gateway_url',
        required=True,
        encrypted=False,
        default='https://api.manage.trellix.com',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'client_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'client_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'trellix_epo_events',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'trellix_audit_events',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'trellix_insights_events',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'trellix_dlp_incidents',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'trellix_edr_events',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'trellix_data_source',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
