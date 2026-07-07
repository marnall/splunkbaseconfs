"""TA-cisco_catalyst_ise_administrative_input."""
import logging
import import_declare_test  # noqa: F401
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

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
        'ise_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        'ise_disk_repo',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'ise_sftp_repo',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'repo_path',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        "logging_level", 
        required=False, 
        encrypted=False, 
        default="INFO", 
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
    "cisco_catalyst_ise_analytics_reports",
    model,
)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
