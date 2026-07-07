import ta_netskopeappforsplunk_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)

from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from utils_storage_account import (
    StorageAccountModel,
    StorageAccountHandler,
    ConnectionStringValidator,
    DestContainerValidator,
)

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        "connection_string",
        required=True,
        encrypted=True,
        default=None,
        validator=ConnectionStringValidator(),
    ),
    field.RestField(
        "dest_container_name",
        required=True,
        encrypted=False,
        default=None,
        validator=DestContainerValidator(),
    )
]
model = RestModel(fields, name=None)

endpoint = StorageAccountModel(
    "ta_netskopeappforsplunk_storage_account",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=StorageAccountHandler,
    )
