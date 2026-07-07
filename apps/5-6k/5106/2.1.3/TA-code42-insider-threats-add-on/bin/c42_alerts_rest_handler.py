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
        "c42_search_behavior",
        required=True,
        encrypted=False,
        default="all",
        validator=None,
    ),
    field.RestField(
        "severity_low", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "severity_medium", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "severity_high", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField(
        "risk_severity_low",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "risk_severity_moderate",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "risk_severity_high",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "risk_severity_critical",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "add_file_events", required=False, encrypted=False, default=None, validator=None
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)
endpoint = DataInputModel(
    "c42_alerts",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=admin_external.AdminExternalHandler,
    )
