import ta_opswat_metaaccess_declare

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
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'api_endpoint',
        required=True,
        encrypted=False,
        default='/o/api/v3/logs',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'start_date',
        required=True,
        encrypted=False,
        default='7',
        validator=validator.Pattern(
            regex=r"""^[1-2]\d|30|\d$""",
        )
    ),
    field.RestField(
        'filter',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'event_trigger',
        required=True,
        encrypted=False,
        default='noncompliant',
        validator=None
    ),
    field.RestField(
        'device_details_endpoint',
        required=True,
        encrypted=False,
        default='/o/api/v3.4/devices/detail',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'device_details_body',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'vulnerabilities_endpoint',
        required=True,
        encrypted=False,
        default='/o/api/v3/get_cves',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'vulnerabilities_body',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'retrieve_device_details',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'retrieve_vulnerabilities',
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
    'metaaccess_device_logs',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )

