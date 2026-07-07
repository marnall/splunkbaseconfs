"""Custom REST handler for CTIX accounts with validation."""
import ta_cyware_ctix_declare  # noqa: F401

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.error import RestError

from cyware_account_validator import validate_ctix_account
import ta_cyware_ctix.logging_helper as logging_helper

util.remove_http_proxy_env_vars()

# Logger
logger = logging_helper.get_logger("account_handler")

fields = [
    field.RestField(
        'base_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    ),
    field.RestField(
        'access_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    ),
    field.RestField(
        'secret_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    ),
]

model = RestModel(fields, name=None)

endpoint = SingleModel(
    'ta_cyware_ctix_account',
    model,
)


class AccountHandler(admin_external.AdminExternalHandler):
    """Custom REST handler for CTIX accounts with validation."""

    def handleCreate(self, confInfo):
        """Handle account creation with validation.

        Args:
            confInfo (dict): Configuration information
        Returns:
            dict: Configuration information
        """
        # Extract credentials from payload
        base_url = self.payload.get("base_url", "").strip()
        access_id = self.payload.get("access_id", "").strip()
        secret_key = self.payload.get("secret_key", "").strip()

        # Validate account credentials
        validation_result = validate_ctix_account(base_url, access_id, secret_key)

        if not validation_result["valid"]:
            # Log detailed error
            account_name = self.callerArgs.id or "new_account"
            logger.error(
                "Account validation failed: account_name=%s, error_code=%s, status=%s, details=%s",
                account_name,
                validation_result["error_code"],
                validation_result["status_code"],
                validation_result["detailed_error"]
            )

            # Raise RestError with user-friendly message
            raise RestError(
                400,
                validation_result["user_message"]
            )

        # Validation passed, proceed with creation
        logger.info("Account validation successful for account: %s", self.callerArgs.id)
        return super(AccountHandler, self).handleCreate(confInfo)

    def handleEdit(self, confInfo):
        """Handle account update with validation.

        Args:
            confInfo (dict): Configuration information
        Returns:
            dict: Configuration information
        """
        # Check if this is a disable/enable operation
        disabled = self.payload.get("disabled")
        if disabled is not None:
            # Disable/enable operations don't need validation
            return super(AccountHandler, self).handleEdit(confInfo)

        # Extract credentials from payload
        # For updates, get existing values if not provided
        base_url = self.payload.get("base_url", "").strip()
        access_id = self.payload.get("access_id", "").strip()
        secret_key = self.payload.get("secret_key", "").strip()

        # Only validate if we have all required fields
        if base_url and access_id and secret_key:
            validation_result = validate_ctix_account(base_url, access_id, secret_key)

            if not validation_result["valid"]:
                # Log detailed error
                logger.error(
                    "Account validation failed: account_name=%s, error_code=%s, status=%s, details=%s",
                    self.callerArgs.id,
                    validation_result["error_code"],
                    validation_result["status_code"],
                    validation_result["detailed_error"]
                )

                # Raise RestError with user-friendly message
                raise RestError(
                    400,
                    validation_result["user_message"]
                )

            # Validation passed
            logger.info("Account validation successful for account: %s", self.callerArgs.id)

        # Proceed with update
        return super(AccountHandler, self).handleEdit(confInfo)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AccountHandler,
    )
