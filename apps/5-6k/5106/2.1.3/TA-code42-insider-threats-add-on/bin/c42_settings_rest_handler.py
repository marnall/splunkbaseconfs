import lib_path
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external


fields_logging = [
    field.RestField(
        "loglevel", required=False, encrypted=False, default="INFO", validator=None
    )
]


model_logging = RestModel(fields_logging, name="logging")
endpoint = MultipleModel(
    "ta_code42_insider_threats_add_on_settings",
    models=[model_logging],
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=admin_external.AdminExternalHandler,
    )
