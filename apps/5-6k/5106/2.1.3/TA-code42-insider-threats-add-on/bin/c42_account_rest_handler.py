import lib_path
import os
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError
from requests.exceptions import ProxyError

import c42_util
from incydr import Client
from splunktaucclib.rest_handler.error import RestError
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external
from solnlib import log

get_logger = log.Logs().get_logger


class AccountModel(SingleModel):
    def validate(self, name, data, existing=None):
        super(AccountModel, self).validate(name, data, existing=existing)
        logger = get_logger("ta_code42_insider_threats_add_on_c42_account")
        domain = data.get("c42_domain")
        if not domain[0:4] == "http":
            domain = f"https://{domain}"
        api_client_id = data.get("api_client_id")
        api_client_secret = data.get("api_client_secret")
        proxies = c42_util.construct_proxies(
            data.get("proxy_address"), data.get("proxy_auth")
        )
        try:
            if proxies:
                os.environ["http_proxy"] = proxies["http"]
                os.environ["https_proxy"] = proxies["https"]
            Client(
                url=domain,
                api_client_id=api_client_id,
                api_client_secret=api_client_secret,
            )
        except ProxyError as e:
            logger.info(f"Problem validating Code42 Account: {e}")
            if "407 Proxy Authentication Required" in str(e):
                msg = "Proxy Authentication failed. Check credentials and retry."
            else:
                msg = "Connection attempt failed. Check Code42 domain and/or proxy address and retry."
            raise RestError(400, msg)
        except HTTPError as e:
            logger.info(f"Problem validating Code42 Account: {e}")
            if e.response.status_code == 407:
                msg = "Proxy Authentication failed. Check proxy auth credentials and retry."
            elif e.response.status_code == 401:
                msg = "Code42 Authentication failed. Check API Client ID and Secret and retry."
            else:
                msg = "Unknown problem authenticating. Check logs for details."
            raise RestError(400, msg)
        except ConnectionError as e:
            logger.info(f"Problem validating Code42 Account: {e}")
            msg = "Connection to Code42 domain failed. Check address and retry."
            raise RestError(400, msg)
        except Exception as e:
            logger.info(f"Problem validating Code42 Account: {e}")
            msg = "Unknown problem authenticating. Check logs for details."
            raise RestError(400, msg)


fields = [
    field.RestField(
        "api_client_id",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        ),
    ),
    field.RestField(
        "api_client_secret",
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        ),
    ),
    field.RestField(
        "c42_domain",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Host(),
    ),
    field.RestField(
        "proxy_address",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(r"https?://.*"),
    ),
    field.RestField(
        "proxy_auth",
        required=False,
        encrypted=True,
        default=None,
        validator=validator.Pattern(r".+:.+"),
    ),
]
model = RestModel(fields, name=None)
endpoint = AccountModel(
    "ta_code42_insider_threats_add_on_account",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=admin_external.AdminExternalHandler,
    )
