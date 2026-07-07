
import ta_aiops_sfcc_logs_declare

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
        'ocapi_credentials',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'auth_headers',
        required=False,
        encrypted=True,
        default=None,
        validator=None
    ),
    field.RestField(
        'webdav_host_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'webdav_endpoint',
        required=True,
        encrypted=False,
        default=None
    ),
    field.RestField(
        'days_threshold',
        required=True,
        encrypted=False,
        default='1',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'system_log_files_pattern',
        required=True,
        encrypted=False,
        default='^(error|warn|info)-.*',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'custom_log_files_pattern',
        required=True,
        encrypted=False,
        default='^custom(error|warn|info)-.*',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'jobs_log_files_pattern',
        required=True,
        encrypted=False,
        default='^jobs-.*',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'services_log_files_pattern',
        required=True,
        encrypted=False,
        default='^service-.*',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'replication_log_files_pattern',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'other_log_files_pattern',
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
    'salesforce_commerce_cloud_logs_v2',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
