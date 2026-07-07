
import intrigue_declare

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
        default=False,
        validator=validator.Pattern(
            regex=r"""^(21[6-8][0-9]{2}|219[0-8][0-9]|2199[0-9]|2[2-9][0-9]{3}|3[0-9]{4}|4[0-2][0-9]{3}|43[01][0-9]{2}|43200)$""",
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
        'collection_name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'item_type',
        required=True,
        encrypted=False,
        default='entities',
        validator=None
    ),
    field.RestField(
        'access_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'secret_key',
        required=True,
        encrypted=True,
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
    'Intrigue',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
