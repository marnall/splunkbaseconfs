"""This file is used for validating JupiterOne account and input."""
import ta_jupiterone_declare  # noqa F401
from splunktaucclib.rest_handler.endpoint.validator import Validator
from ta_jupiterone_log_manager import setup_logging
import ta_jupiterone_constants as constants
from ta_jupiterone_utils import get_proxy
from datetime import datetime
import traceback
import requests


def mask_sensitive_headers(headers):
    """Mask sensitive information in headers for logging purposes."""
    masked_headers = headers.copy()
    if 'Authorization' in masked_headers:
        auth_value = masked_headers['Authorization']
        if auth_value.startswith('Bearer '):
            # Keep first 8 and last 4 characters, mask the rest
            token = auth_value[7:]  # Remove 'Bearer ' prefix
            if len(token) > 12:
                masked_token = token[:8] + '*' * (len(token) - 12) + token[-4:]
            else:
                masked_token = '*' * len(token)
            masked_headers['Authorization'] = f'Bearer {masked_token}'
        else:
            masked_headers['Authorization'] = '***MASKED***'
    return masked_headers


logger = setup_logging('ta_jupiterone_validation')


class AccountValidator(Validator):
    """This class validates JupiterOne account."""

    def __init__(self, *args, **kwargs):
        """Param: validator: user-defined validating function."""
        super(AccountValidator, self).__init__()

    def validate(self, value, data):
        """Validate JupiterOne account account_id, base_url, and api_key."""
        # Fetching value from account page.
        account_id = data['account_id']
        base_url = data['base_url']
        if not base_url:
            base_url = constants.BASE_URL
        api_key = "Bearer {}".format(data['api_key'])

        # These are used in API call
        query = """
        query {
            __schema {
                queryType {
                    name
                }
            }
        }
        """
        url = base_url
        header = {
            "JupiterOne-Account": account_id,
            "Authorization": api_key,
        }
        proxy = get_proxy(self)
        
        # Log validation attempt details (with masked sensitive information)
        logger.info("JupiterOne Info: Attempting to validate account with URL: {}".format(url))
        masked_headers = mask_sensitive_headers(header)
        logger.debug("JupiterOne Debug: Validation request - URL: {}, Account ID: {}, Headers: {}".format(url, account_id, masked_headers))
        
        # Making post call
        try:
            response = requests.post(
                url,
                json={"query": query},
                headers=header,
                proxies=proxy,
            )
            if response.status_code in (200, 201, ):
                logger.info("Account is validated.")
                return True
            elif response.status_code in (401, ):
                self.put_msg("Connection Unsuccessful. Verify your Account Id and API Key are correct.")
                logger.error("Invalid JupiterOne Account credentials.")
                return False
            elif response.status_code == 404:
                self.put_msg("API endpoint not found. Please verify the Base URL is correct.")
                logger.error("JupiterOne API endpoint not found. Status code: 404")
                return False
            elif response.status_code == 403:
                self.put_msg("Access forbidden. Please verify your API key has the necessary permissions.")
                logger.error("JupiterOne access forbidden. Status code: 403")
                return False
            elif response.status_code >= 500:
                self.put_msg("JupiterOne server error. Please try again later or contact JupiterOne support.")
                logger.error("JupiterOne server error. Status code: {}".format(response.status_code))
                return False
            else:
                self.put_msg("Unexpected response from JupiterOne. Status code: {}. Please verify your configuration.".format(response.status_code))
                logger.error("Unexpected JupiterOne response. Status code: {} Response: {}".format(response.status_code, response.text))
                return False
        except requests.exceptions.SSLError as sslerror:
            self.put_msg(
                "SSL certificate verification failed. Please add a valid "
                "SSL certificate."
            )
            logger.error(
                "JupiterOne Error: Error occurred while validating JupiterOne account: {0}"
                .format(sslerror)
            )
            logger.debug(
                "JupiterOne Debug: Error occurred while validating JupiterOne account: {0}"
                .format(traceback.format_exc())
            )
            return False
        except requests.exceptions.ProxyError as proxyerror:
            self.put_msg("Invalid Proxy credentials. Please recheck your Proxy settings.")
            logger.error(
                "JupiterOne Error: Error occurred while validating JupiterOne account: {0}"
                .format(proxyerror)
            )
            logger.debug(
                "JupiterOne Debug: Error occurred while validating JupiterOne account: {0}"
                .format(traceback.format_exc())
            )
            return False
        except Exception as e:
            self.put_msg(
                "Unexpected error occurred. Please check `ta_jupiterone_validation.log` file for more details."
            )
            logger.error(
                " JupiterOne Error: Unexpected error occurred while validating JupiterOne account: {0}"
                .format(e)
            )
            logger.debug(
                "JupiterOne Debug: Unexpected error occurred while validating JupiterOne account: {0}"
                .format(traceback.format_exc())
            )
            return False


class IntervalValidator(Validator):
    """This class validates if the interval passed for validation in input is valid or not."""

    def validate(self, value, data):
        """We define Custom validation here for verifying interval field."""
        try:
            interval = int(value)
            if interval < 60:
                self.put_msg("Interval must be greater than or equal to 60.")
                logger.error("JupiterOne Error: Interval must be greater than or equal to 60.")
                return False
        except ValueError:
            self.put_msg("Invalid Interval. Please enter valid interval.")
            logger.error("JupiterOne Error: Invalid Interval. Please enter valid interval.")
            return False
        return True


class DateTimeValidator(Validator):
    """This class validates if the date and time is in future or not and validate the format."""

    def validate(self, value, data):
        """We define Custom validation here for verifying start_datetime field."""
        try:
            if value is not None:
                input_date = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
                now = datetime.utcnow()
                if input_date > now:
                    self.put_msg("Start DateTime should not be in future.")
                    logger.error("JupiterOne Error: Start DateTime should not be in future.")
                    return False
        except ValueError:
            self.put_msg("Start DateTime should be in 'YYYY-MM-DDTHH:MM:SS.SSS' (UTC) format.")
            logger.error("JupiterOne Error: Start DateTime should be in 'YYYY-MM-DDTHH:MM:SS.SSS' (UTC) format.")
            return False
        return True
