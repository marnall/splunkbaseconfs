import lib_path
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external


fields = [
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=28800,
        validator=validator.Number(min_val=300, is_int=True),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.String(
            min_len=1,
            max_len=80,
        ),
    ),
    field.RestField(
        "c42_account", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)
endpoint = DataInputModel(
    "c42_device_health",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=admin_external.AdminExternalHandler,
    )
