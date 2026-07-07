"""This file is used for validating CyCognito account and input."""
import json
import traceback
import requests
from splunktaucclib.rest_handler.endpoint.validator import Validator
import ta_cycognito_constants as constants
import ta_cycognito_declare  # noqa F401
from ta_cycognito_logger_manager import setup_logging
from ta_cycognito_utils import get_proxy

logger = setup_logging("ta_cycognito_validation")


class AccountValidator(Validator):
    """This class validates CyCognito account."""

    def __init__(self, *args, **kwargs):
        """Param: validator: user-defined validating function."""
        super(AccountValidator, self).__init__()

    def validate(self, value, data):
        """Validate API Token for CyCognito account."""
        try:
            # Fetching proxy details
            proxy = get_proxy()
            # Request to authenticate API Token
            response = requests.post(
                url='https://'
                    + data.get('platform_url')
                    + constants.ASSETS_ENDPOINT + '/ip',
                headers={
                    "Authorization": data.get('api_token'),
                    "Content-Type": "application/json",
                    "Accept": "application/json", },
                params={'count': 1},
                data=json.dumps([]),
                verify=constants.SSL_VERIFY,
                timeout=constants.REQ_TIMEOUT,
                proxies=proxy
            )
            if response.status_code == 200:
                logger.info("CyCognito Validation: API Token is validated.")
                return True
            elif response.status_code == 401:
                self.put_msg(
                    "Connection Unsuccessful. Ensure your 'API Token' is correct.")
                logger.error(
                    "CyCognito Validation: Invalid CyCognito API Token. Status code: 401 & Error:\"{}\"".
                    format(response.text))
            elif response.status_code in list(range(400, 500)):
                self.put_msg("Connection Unsuccessful. Status code: {} & Error: {}".format(
                    response.status_code, response.text))
                logger.error("CyCognito Validation: Connection Unsuccessful. Status code={} & Error=\"{}\"".format(
                    response.status_code, response.text))
            elif response.status_code in list(range(500, 600)):
                self.put_msg("Connection Unsuccessful. Server Error. Status code={} & Error=\"{}\"".format(
                    response.status_code, response.text))
                logger.error("CyCognito Validation: Server Error. Status code={} & Error=\"{}\"".format(
                    response.status_code, response.text))
            else:
                raise Exception
        except requests.exceptions.SSLError as sslerror:
            self.put_msg(
                "SSL certificate verification failed. Please add a valid "
                "SSL certificate."
            )
            logger.error(
                "CyCognito Validation: Error occurred while validating CyCognito account: {0}"
                .format(sslerror)
            )
            logger.error(
                "CyCognito Validation: Error occurred while validating CyCognito account: {0}"
                .format(traceback.format_exc())
            )
        except requests.exceptions.ProxyError as proxyerror:
            self.put_msg(
                "Could Not Establish Connection. Please recheck 'Platform URL' credentials or 'Proxy' settings.")
            logger.error(
                "CyCognito Error: Error occurred while validating CyCognito account: {0}"
                .format(proxyerror)
            )
            logger.error(
                "CyCognito Error: Error occurred while validating CyCognito account: {0}"
                .format(traceback.format_exc())
            )
        except requests.exceptions.ConnectionError as connectionerror:
            self.put_msg(
                "Could Not Establish Connection. Please recheck 'Platform URL' credentials or 'Proxy' settings.")
            logger.error(
                "CyCognito Error: Error occurred while validating CyCognito account: {0}"
                .format(connectionerror)
            )
            logger.error(
                "CyCognito Error: Error occurred while validating CyCognito account: {0}"
                .format(traceback.format_exc())
            )
        except Exception as e:
            if '_ssl' in str(e):
                self.put_msg(
                    "SSL certificate verification failed. Please add a valid SSL certificate."
                )
                logger.error(
                    "CyCognito Validation: Error occurred while validating CyCognito account: {0}".format(e)
                )
                logger.error(
                    "CyCognito Validation: Unexpected error occurred while validating CyCognito account: {0}"
                    .format(traceback.format_exc())
                )
            else:
                self.put_msg(
                    "Unexpected error occurred. Please check `ta_cycognito_validation.log` file for more details."
                )
                logger.error(
                    " CyCognito Validation: Unexpected error occurred while validating CyCognito account: {0}"
                    .format(e)
                )
                logger.error(
                    "CyCognito Validation: Unexpected error occurred while validating CyCognito account: {0}"
                    .format(traceback.format_exc())
                )
        return False


class IntervalValidator(Validator):
    """This class validates if the interval passed for validation in input is valid or not."""

    def validate(self, value, data):
        """We define Custom validation here for verifying interval field."""
        try:
            interval = int(value)
            if interval < 86400:
                self.put_msg(
                    "'Interval' must be greater than or equal to 86400.")
                logger.error(
                    "CyCognito Validation: Interval must be greater than or equal to 86400.")
                return False
        except ValueError:
            self.put_msg("Invalid 'Interval'. Please enter valid interval.")
            logger.error(
                "CyCognito Validation: Invalid Interval. Please enter valid interval.")
            return False
        return True
