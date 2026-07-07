import os
import requests
import common.proxy as pro
import common.log as log
import common.utility as utility

from splunktaucclib.rest_handler.endpoint.validator import Validator

logger = log.get_logger("ta_sonrai_account_validation")

APP_NAME = __file__.split(os.sep)[-3]


class ValidateStartTime(Validator):
    """Validator class to validate Start time."""

    def validate(self, value, data):
        """Validation method to validate Start time."""
        validation_flag, msg = utility.validate_start_time(data.get('start_time'))
        if not validation_flag:
            self.put_msg("{}".format(msg))
            return False
        return True


class ValidateSonraiCreds(Validator):
    """Validator class to validate Sonrai Credentials."""

    def validate(self, value, data):
        """Validation method to validate Sonrai Credentials."""
        try:
            data['verify_certs'] = True
            organization_id = data.get('organization_id')
            token = data.get('sonrai_token')
            iat_time, exp_time = utility.sonrai_token_decode(token)
            token_expiration_in_seconds = exp_time - iat_time
            sonrai_host = data.get("sonrai_host")
            headers = utility.get_headers(token, "SonraiAPIClient_TokenRenew")
            payload = utility.get_renew_account_payload(token_expiration_in_seconds)
            request_url = utility.get_host_url(organization_id, sonrai_host)
            logger.info(request_url)
            proxy_settings = pro.read_proxies_from_conf()
            response = requests.post(
                request_url,
                data=payload,
                headers=headers,
                proxies=proxy_settings,
                timeout=30
            )
            response.raise_for_status()
            if response.status_code in (200, 201):
                retrived_token = response.json().get("data", {}).get("GenerateSonraiUserToken", {}).get("token")
                if retrived_token is not None:
                    data['sonrai_token'] = retrived_token
                    logger.info("message=creds_correct | Account created successfully.")
                    return True
                else:
                    logger.error("message=creds_incorrect | 200 status code received, but token not present.")
                    return False
        except requests.exceptions.SSLError:
            self.put_msg(
                "SSL certificate verification failed. Please add a valid "
                "SSL Certificate or Change VERIFY_SSL flag to False"
            )
            return False
        except Exception as e:
            if "response" in locals() and response.status_code == 401:
                msg = "Invalid Token."\
                    "Please enter the valid credentials."
            elif "response" in locals() and response.status_code == 404:
                msg = "Please validate the provided details."
            elif "response" in locals() and response.status_code == 429:
                msg = "API limit has exceeded. Please retry after some time."
            elif "response" in locals() and response.status_code == 500:
                msg = "Internal server error. Cannot verify Sonrai instance."
            else:
                msg = "Unable to request Sonrai instance. "\
                    "Please validate the provided credentials and "\
                    "Proxy configurations or check the network connectivity."
                msg = "{} {}".format(msg, e)
            self.put_msg(msg)
            logger.error("msg=creds_incorrect | Account not created | Error: {}".format(e))
        return False
