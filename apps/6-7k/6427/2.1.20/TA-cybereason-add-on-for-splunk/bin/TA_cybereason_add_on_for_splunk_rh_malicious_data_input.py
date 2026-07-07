
import ta_cybereason_add_on_for_splunk_declare

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
        'base_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'hist_days',
        required=True,
        encrypted=False,
        default='365',
        validator=validator.Number(
            min_val=0,
            max_val=1825,
            is_int=True
        )
    ), 
    field.RestField(
        'buffer_time',
        required=True,
        encrypted=False,
        default='7200',
        validator=validator.Number(
            is_int=True
        )
    ),
    field.RestField(
        'authentication_type',
        required=True,
        encrypted=False,
        default='basic',
        validator=None
    ), 
    field.RestField(
        'group_name',
        required=False,
        encrypted=False,
        default=None
    ), 
    field.RestField(
        'ssl_certificate_path',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'malops',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'suspicious_objects',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'malware',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'pull_comments',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    ),
    field.RestField(
        'select_malop_status',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'malicious_data_input',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
