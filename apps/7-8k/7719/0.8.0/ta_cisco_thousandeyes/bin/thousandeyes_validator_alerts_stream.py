import import_declare_test  # noqa F401

import traceback

from splunktaucclib.rest_handler.error import RestError
from solnlib.hec_config import HECConfig
from solnlib.utils import is_false
from thousandeyes_client import ThousandEyesClient
from thousandeyes_utils import get_account_id, get_hec_tokens


class AlertsStreamValidator:
    """
    Validator for Alerts Stream Input.
    """

    def __init__(self, session_key, logger):
        """
        Initialize the validator.

        :param session_key: session key for authentication
        :param logger: logger instance
        """
        self.session_key = session_key
        self.logger = logger

    def validate(self, payload):
        """
        Validate the alerts stream input configuration.

        :param payload: configuration payload
        :raises RestError: if validation fails
        """
        try:
            self.logger.info("Validating alerts stream input configuration")

            # Validate HEC target and token
            if payload.get("hec_target") and payload.get("hec_token"):
                self._validate_hec_configuration(payload)

            self.logger.info(
                "Alerts stream input configuration validation completed successfully"
            )

        except RestError:
            raise
        except Exception as e:
            self.logger.error(
                f"Error validating alerts stream input: {str(e)} {traceback.format_exc()}"
            )
            raise RestError(400, f"Error validating alerts stream input: {str(e)}")

    def _validate_hec_configuration(self, payload):
        """Validate HEC target and token configuration"""
        try:
            hec_token = payload["hec_token"]

            # Validate HEC token exists in configured tokens
            hec_list = get_hec_tokens(self.session_key)
            if hec_token not in hec_list.keys():
                self.logger.error(
                    f"Configured HEC token: {hec_token} is not valid. Please verify."
                )
                raise RestError(
                    400,
                    f"Configured HEC token: {hec_token} is not valid. Please verify.",
                )

            # Check if HEC SSL is enabled
            hec_settings = HECConfig(session_key=self.session_key).get_settings()
            if is_false(hec_settings.get("enableSSL")):
                self.logger.error(
                    "SSL for HTTP Event Collector not enabled. "
                    "Please enable SSL for HTTP Event Collector."
                )
                raise RestError(
                    400,
                    "SSL for HTTP Event Collector not enabled. "
                    "Please enable SSL for HTTP Event Collector.",
                )

            self.logger.info(f"Successfully validated HEC Token: {hec_token}")

        except RestError:
            raise
        except Exception as e:
            self.logger.error(f"Error validating HEC configuration: {str(e)}")
            raise RestError(400, f"Error validating HEC configuration: {str(e)}")
