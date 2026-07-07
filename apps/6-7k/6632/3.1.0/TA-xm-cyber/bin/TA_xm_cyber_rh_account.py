import import_declare_test  # noqa: F401
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from xmcyber_account_validation import account_validation_oauth
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError
from log_helper import setup_logging
from xmcyber.exceptions import APIKeyError
from import_declare_test import ta_prefix
import traceback

import logging
import requests

util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""",
            ),
            validator.String(
                max_len=100,
                min_len=1,
            )
        )
    )
]

fields = [
    field.RestField(
        'base_url',
        required=True,
        encrypted=False,
        validator=validator.Pattern(
            regex=r"^(?!https?://).+"
        )
    ),
    field.RestField(
        'auth_type',
        required=False,
        encrypted=False,
        default='oauth',
        validator=None
    ),
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None
    ),
    field.RestField(
        'access_token',
        required=False,
        encrypted=True,
        default=None
    ),
    field.RestField(
        'refresh_token',
        required=False,
        encrypted=True,
        default=None
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_xm_cyber_account',
    model,
    config_name='account'
)


class TAXMCyberAccountHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self.logger = setup_logging(f"{ta_prefix}_account_validation")


    def _validate_and_set_tokens(self):
        self.logger.info("Starting token validation and setting process")
        try:
            oauth_response = account_validation_oauth(
                self.payload.get("api_key"),
                self.getSessionKey(),
                self.payload.get('base_url'),
                self.logger
            )
            # OAuth-only: only persist auth_type as oauth after OAuth validation succeeds.
            self.payload["auth_type"] = "oauth"
            self.payload["refresh_token"] = oauth_response.get("refreshToken")
            self.payload["access_token"] = oauth_response.get("accessToken")
        except APIKeyError as e:
            self.logger.error(f"Error: {e} Traceback: {traceback.format_exc()}")
            raise RestError(400, e)
        except requests.exceptions.InvalidHeader:
            self.logger.error(f"API Key Error: Enter a valid API key. Traceback: {traceback.format_exc()}")
            raise RestError(400, "API Key Error: Enter a valid API key.")
        except Exception as e:
            self.logger.error(f"Error: {e} Traceback: {traceback.format_exc()}")
            raise RestError(400, e)

    def handleEdit(self, confinfo):
        self._validate_and_set_tokens()
        AdminExternalHandler.handleEdit(self, confinfo)

    def handleCreate(self, confinfo):
        self._validate_and_set_tokens()
        AdminExternalHandler.handleCreate(self, confinfo)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=TAXMCyberAccountHandler,
    )
