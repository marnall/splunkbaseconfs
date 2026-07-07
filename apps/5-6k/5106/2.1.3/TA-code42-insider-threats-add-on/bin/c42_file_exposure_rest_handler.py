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
        default=300,
        validator=validator.Number(min_val=300, is_int=True),
    ),
    field.RestField(
        "delay_interval",
        required=False,
        encrypted=False,
        default=0,
        validator=validator.Number(min_val=0, is_int=True),
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
    field.RestField(
        "min_risk_score",
        required=True,
        encrypted=False,
        default=1,
        validator=validator.Number(min_val=0, is_int=True),
    ),
    field.RestField(
        "saved_search_id",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(),
    ),
    field.RestField("disabled", required=False, validator=None),
    field.RestField(
        "page_size", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "days_back", required=False, encrypted=False, default=None, validator=None
    ),
]
model = RestModel(fields, name=None)
endpoint = DataInputModel(
    "c42_file_exposure",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=admin_external.AdminExternalHandler,
    )
