
import ta_risksense_declare
from interval_validation import IntervalValidator
from filters_validation import FilterValidator

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
        validator=IntervalValidator()
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
        'risksense_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'finding_type',
        required=True,
        encrypted=False,
        default='hosts',
        validator=None
    ), 
    field.RestField(
        'filters',
        required=False,
        encrypted=False,
        default=None,
        validator=FilterValidator()
    ), 
    field.RestField(
        'page_size',
        required=True,
        encrypted=False,
        default='20',
        validator=validator.Pattern(
            regex=r"""^(1000|[1-9][0-9][0-9]?|[1-9][0-9]?)$""", 
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
    'risksense',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
