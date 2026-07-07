
import ta_gigamon_insight_add_on_for_splunk_declare

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
        'start_date',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'account_uuid',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'status',
        required=False,
        encrypted=False,
        default='active',
        validator=None
    ), 
    field.RestField(
        'severity_levels',
        required=False,
        encrypted=False,
        default='high~moderate~low',
        validator=None
    ), 
    field.RestField(
        'confidence_levels',
        required=False,
        encrypted=False,
        default='high~moderate~low',
        validator=None
    ), 
    field.RestField(
        'pull_muted_rules',
        required=False,
        encrypted=False,
        default='false',
        validator=None
    ), 
    field.RestField(
        'pull_muted_devices',
        required=False,
        encrypted=False,
        default='false',
        validator=None
    ), 
    field.RestField(
        'pull_muted_detections',
        required=False,
        encrypted=False,
        default='false',
        validator=None
    ), 
    field.RestField(
        'include_description',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'include_signature',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'include_pdns',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'include_dhcp',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'include_events',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'filter_training_detections',
        required=False,
        encrypted=False,
        default=True,
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
    'insight_detections',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
