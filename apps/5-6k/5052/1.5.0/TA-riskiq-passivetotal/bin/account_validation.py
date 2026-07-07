"""Passivetotal Account Validation."""
import requests
import socks
from requests.auth import HTTPBasicAuth
from splunktaucclib.rest_handler.endpoint.validator import Validator

import passivetotal_utils as utils


class AccountValidator(Validator):
    """Validate the credentials of passivetotal account."""

    def validate(self, value, data):
        """We define validation here for verifying credentials when storing account information."""
        try:
            url = "{}{}".format(utils.BASE_URL, utils.ACCOUNT_ENDPOINT)
            username = data["passivetotal_username"].strip()
            password = value.strip()
            proxies = utils.create_requests_proxy_dict()

            response = requests.get(url, auth=HTTPBasicAuth(
                username, password), proxies=proxies)
            api_message = ""
            try:
                res = response.json()
                api_message = res.get("message")

            except Exception:
                raise Exception("Authentication Failed")

            if api_message:
                raise Exception(api_message)

            response.raise_for_status()

        except (requests.exceptions.ProxyError, socks.ProxyError):
            self.put_msg(
                "Invalid Proxy credentials. Please recheck your Proxy settings.")
            return False

        except requests.exceptions.ConnectionError as err:
            self.put_msg(
                "Please check your network connection OR proxy settings. Cause -> {}."
                .format(err))
            return False

        except Exception as err:
            message = "Please check PassiveTotal Username / API Key. Cause -> {}.".format(err)
            if "invalid credentials" in str(err):
                message = "Invalid credentials. Please check PassiveTotal Username / API Key."

            self.put_msg(message)
            return False
        return True
