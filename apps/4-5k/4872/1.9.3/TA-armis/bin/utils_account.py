"""Utilities related to account page."""
import requests

from splunktaucclib.rest_handler.endpoint.validator import Validator
from proxy_config import read_proxies_from_conf
from log_manager import setup_logging

logger = setup_logging("proxy_conf")


class KeyValidator(Validator):
    """To validate Api key of Armis Hostname."""

    def validate(self, value, data):
        """Validate api key given by user."""
        armis_api = data.get("armis_api_key")
        armis_host = data.get("armis_hostname")
        try:
            url = "https://%s/api/v1/access_token/" % (armis_host)
            data = {"secret_key": armis_api}
            proxy_settings = read_proxies_from_conf()
            if proxy_settings:
                logger.info("Account:Proxy is Enabled")
            else:
                logger.info("Account:Proxy is Disabled")
            r = requests.post(url, data=data, proxies=proxy_settings)
            r.raise_for_status()

            return True

        except Exception:
            if "r" in locals() and r.status_code == 400:
                msg = "Invalid Armis API Key. Please enter valid credentials."
            elif "r" in locals() and r.status_code == 404:
                msg = "Please validate the provided details."
            elif "r" in locals() and r.status_code == 429:
                msg = "API limit has exceeded. Please retry after some time."
            elif "r" in locals() and r.status_code == 500:
                msg = "Internal server error."
            else:
                msg = (
                    "Unable to request Armis instance. "
                    "Please verify the provided Armis Hostname or "
                    "Please verify Proxy settings."
                )

            self.put_msg(msg)
            return False
