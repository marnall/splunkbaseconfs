import logging

import package_helper # keep for added paths
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.endpoint import DataInputModel, RestModel, field, validator

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        "api_token", 
        required=True, 
        encrypted=False, 
        default=None, 
        validator=validator.Pattern(
            regex=r"""^(?=.*[a-zA-Z])\w{1,50}$""", 
        ), 
    ),
    field.RestField(
        "url", 
        required=True, 
        encrypted=False, 
        default=None, 
        validator=validator.Pattern(
            regex=r"""^https:\/\/([a-z0-9]+[-.]*[a-z0-9]+)+\/w\/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\/alerts$""", 
        ),    
    ),
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=300,
        validator=validator.Number(
            max_val=3600,
            min_val=60,
        ),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="main",
        validator=validator.String(
            max_len=80,
            min_len=1,
        ),
    ),
    field.RestField(
        "source",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=100,
            min_len=1,
        ),
    ),
    field.RestField(
        "include_pii",
        encrypted=False,
        required=False,
        default="0",
        validator=validator.Enum(
            values=["0", "1"]
        )
    ),
    field.RestField(
        "disabled", 
        encrypted=False,
        required=False, 
        default=0,
        validator=validator.Enum(
            values=[0, 1]
        )        
    ),
]

endpoint = DataInputModel(
    "beacon_input",
    RestModel(fields, name=None),
)

if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(endpoint)
