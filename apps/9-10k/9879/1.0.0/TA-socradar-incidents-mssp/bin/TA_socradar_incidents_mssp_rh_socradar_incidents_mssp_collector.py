
import ta_socradar_incidents_mssp_declare

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
            regex=r"""^(?:-1|\d+(?:\.\d+)?)$""",
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
        'socradar_api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'multi_tenant_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=80,
            min_len=1,
        )
    ),
    field.RestField(
        'ioc_api_key',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'severity_filter',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'status_filter',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
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
        'excluded_tags',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'alarm_type_ids',
        required=False,
        encrypted=False,
        default=None,
        # Numeric-CSV only (empty allowed). A non-numeric value reaches the v4 API unchanged,
        # returns HTTP 200 with 0 matches and silently drops ALL data (edge-audit e3), so
        # reject it at save time. Mirrors the globalConfig UI regex validator.
        validator=validator.Pattern(
            regex=r"^\s*$|^\s*\d+(\s*,\s*\d+)*\s*$",
        )
    ),

    field.RestField(
        'alarm_main_types',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),

    field.RestField(
        'alarm_sub_types',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),

    field.RestField(
        'include_content',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ),
    field.RestField(
        'include_alarm_details',
        required=False,
        encrypted=False,
        default=False,
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
    'socradar_incidents_mssp_collector',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
