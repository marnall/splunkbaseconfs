
import ta_vuln_db_declare

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
            regex=r"""^[1-9]\d*$""",
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
        'api_server',
        required=True,
        encrypted=False,
        default='https://vulndb.flashpoint.io',
        validator=validator.Pattern(
            regex=r"""^https:\/\/[0-9a-zA-Z]([-\\w]*[.]?[0-9a-zA-Z])*$"""
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
        'api_secret',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'start_date',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\d\d\d\d-\d\d-\d\d$|^1$""",
        )
    ),
    field.RestField(
        'page_size',
        required=True,
        encrypted=False,
        default='100',
        validator=validator.Number(
            min_val=1,
            max_val=100,
        )
    ),
    field.RestField(
        'min_cvssv2_score',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=0,
            max_val=10,
        )
    ),
    field.RestField(
        'reset_input',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'nested',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'additional_info',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'show_cpe',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'category',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'full_reference_url',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ), 
    field.RestField(
        'package_info',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'show_cvss_v3',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),  
    field.RestField(
        'changelog',
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
    'vulndb',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
