"""Validation code for account host name, account credentials and proxy settings."""

import traceback
import requests
import json

from splunktaucclib.rest_handler.endpoint.validator import Validator

from common import proxy, log
import const

logger = log.get_logger(__name__)


class ValidateAccountCreds(Validator):
    """This class validates the Account Credentials."""

    def validate(self, value, data):
        """This method validates the client ID and secret-key."""
        server_url = data["server_url"]
        client_id = data["client_id"]
        client_secret_key = data["client_secret_key"]

        host_url = "https://{}".format(server_url)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        payload = {"grant_type": "client_credentials"}

        try:
            proxy_settings = proxy.read_proxy_config()
            if proxy_settings is not None:
                logger.info("Proxy is enabled.")

            response = requests.post(
                host_url + "/oauth2/token",
                auth=(client_id, client_secret_key),
                headers=headers,
                data=payload,
                proxies=proxy_settings,
                verify=const.VERIFY_SSL,
            )
            response.raise_for_status()

            if response.status_code == 200:
                # check for valid response
                data = json.loads(response.text)
                if not (data.get("access_token") and data.get("refresh_token")):
                    raise Exception("Response does not contain 'access_token' and/or 'refresh_token' field.")

                msg = "Vectra SaaS validation: Account with Host Name - {} " \
                    "added successfully".format(server_url)
                logger.info(msg)
                return True

        except requests.exceptions.SSLError as sslerror:
            self.put_msg(
                "SSL certificate verification failed. Please add a valid "
                "SSL certificate."
            )
            logger.error(
                "Vectra SaaS validation: SSL Error occurred while validating "
                "Vectra SaaS account: {}\n{}"
                .format(sslerror, traceback.format_exc())
            )
            return False

        except requests.exceptions.ProxyError as proxyerror:
            self.put_msg(
                "Invalid Proxy settings or Host Name. "
                "Please recheck your Proxy settings and Host Name."
            )
            logger.error(
                "Vectra SaaS validation: Proxy Error occurred while validating "
                "Vectra SaaS account: {}\n{}"
                .format(proxyerror, traceback.format_exc())
            )
            return False

        except Exception as error:
            if "response" in locals() and response.status_code == 401:
                msg = "Invalid client credentials. " \
                    "Please verify the provided client credentials."
            elif "response" in locals() and response.status_code == 429:
                msg = "API limit has been exceeded. Please retry after some time."
            elif "response" in locals() and response.status_code in range(400, 500):
                msg = "Connection unsuccessful: Status code - {}.".format(
                    response.status_code
                )
            elif "response" in locals() and response.status_code in range(500, 600):
                msg = "Server error: Status code - {}. " \
                    "Cannot verify Vectra SaaS instance. " \
                    "Please try again.".format(response.status_code)
            elif "_ssl.c" in str(error):
                msg = "SSL certificate verification failed. Please add a valid " \
                    "SSL certificate."
            else:
                msg = "Unexpected error occurred. Please verify the Host Name " \
                    "and check `ta_vectra_saas_account_validation.log` file for " \
                    "more details."

            self.put_msg(msg)
            logger.error("Vectra SaaS validation: Error occurred while "
                         "validating Vectra SaaS account: {}\n{}"
                         .format(error, traceback.format_exc()))
            return False
