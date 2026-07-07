
import ta_cyera_declare

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
        'cyera_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'enable_events',
        required=False,
        encrypted=False,
        default='1',
        validator=None
    ),
    field.RestField(
        'enable_issues',
        required=False,
        encrypted=False,
        default='1',
        validator=None
    ),
    field.RestField(
        'enable_datastores',
        required=False,
        encrypted=False,
        default='1',
        validator=None
    ),
    field.RestField(
        'enable_classifications',
        required=False,
        encrypted=False,
        default='0',
        validator=None
    ),
    field.RestField(
        'enable_audit',
        required=False,
        encrypted=False,
        default='1',
        validator=None
    ),
    field.RestField(
        'retrieve_all_datastores',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    # Per-endpoint interval overrides (blank = use base interval)
    field.RestField(
        'interval_events',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'interval_issues',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'interval_datastores',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'interval_classifications',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'interval_audit',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    # Per-endpoint index overrides (blank = use base index)
    field.RestField(
        'index_events',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'index_issues',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'index_datastores',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'index_classifications',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'index_audit',
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
    'cyera_collector',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
