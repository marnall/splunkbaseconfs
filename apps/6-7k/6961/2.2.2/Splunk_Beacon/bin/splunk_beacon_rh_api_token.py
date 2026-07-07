import logging

import package_helper # keep for added paths
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.endpoint import RestModel, SingleModel, field, validator

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        "username", 
        required=True, 
        encrypted=False, 
        default=None, 
        validator=validator.Pattern(
            regex=r"""^[A-Za-z0-9][A-Za-z0-9._%+-]{0,63}@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,62}[A-Za-z0-9])?\.){1,8}[A-Za-z]{2,63}$""",
        ),
    ),
    field.RestField(
        "token", 
        required=True, 
        encrypted=True, 
        default=None, 
        validator=validator.Pattern(
            regex=r"""^.*=[0-9A-F]{8}$""",
        ),
    ),
    field.RestField(
        "help_link", 
        required=False, 
        encrypted=False, 
        default=None, 
        validator=None
    ),
]

endpoint = SingleModel(
    "splunk_beacon_api_token", 
    RestModel(fields, name=None), 
    config_name="api_token"
)

if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(endpoint)
