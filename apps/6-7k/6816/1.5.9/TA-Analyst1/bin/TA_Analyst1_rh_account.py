import ta_analyst1_declare  # noqa:F401
import json
import os
import re
import sys
import time
import traceback

# Add path for custom credentials class
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ta_analyst1'))

from analyst1_helpers.conf_helper import get_conf_file, get_proxy_info
from analyst1_helpers.constants import CERT_FILE_LOC
from analyst1_oauth_helper import Analyst1OAuth
from analyst1_helpers.validators import AccountValidator
from analyst1_logging import get_logger
from splunk_client.splunk_service_adapter import SplunkServiceAdapter
from solnlib.utils import is_true
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunk_client.splunk_ta_conf.analyst1_rest_credentials import Analyst1RestCredentials
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler.error import RestError
from splunktaucclib.rest_handler.handler import RestHandler

logger = get_logger("ta_analyst1_rest_handler")


util.remove_http_proxy_env_vars()


class Analyst1AccountRestHandler(RestHandler):
    """
    Custom REST handler for accounts that uses Analyst1RestCredentials to prevent OAuth token corruption.

    This handler prevents OAuth fields from being incorrectly processed during account operations.
    OAuth fields (access_token, token_expiry) are managed by the OAuth helper and stored in the
    conf file, not in passwords.conf. This handler ensures they're not incorrectly decrypted.
    """

    def __init__(self, splunkd_uri, session_key, endpoint, *args, **kwargs):
        # Call parent constructor
        super().__init__(splunkd_uri, session_key, endpoint, *args, **kwargs)

        # Replace the default RestCredentials with our custom implementation
        # This prevents OAuth token corruption during account operations
        self.rest_credentials = Analyst1RestCredentials(
            splunkd_uri,
            session_key,
            endpoint,
        )

    def _sanitize_error_message(self, message, access_token=None):
        """
        Remove sensitive token data from error messages.

        This prevents OAuth tokens from being leaked in logs or error messages.
        Sanitizes:
        - The specific access token if provided
        - JWT-like patterns (eyJ...)
        - Long base64 strings that could be tokens

        Args:
            message: Error message to sanitize
            access_token: Optional specific token to redact

        Returns:
            str: Sanitized message with tokens redacted
        """
        if not message:
            return message

        # Redact the specific token if provided
        if access_token and access_token in message:
            message = message.replace(access_token, '[REDACTED_TOKEN]')

        # Redact any JWT-like patterns (eyJ...)
        message = re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[REDACTED_JWT]', message)

        # Redact long base64 strings (potential tokens) - but be conservative
        # Only redact if 60+ chars (shorter strings could be legitimate IDs)
        message = re.sub(r'[A-Za-z0-9+/=]{60,}', '[REDACTED_TOKEN]', message)

        return message


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server with OAuth-safe credentials handling.
    :param ConfigMigrationHandler: inhereting ConfigMigrationHandler
    """

    # Fields that should have whitespace stripped before saving
    STRIP_WHITESPACE_FIELDS = ['client_id', 'client_secret', 'server_address', 'username', 'password']

    def __init__(self, *args, **kwargs):
        """
        Override initialization to inject custom REST handler with OAuth protection.
        """
        # Call parent __init__ first
        super().__init__(*args, **kwargs)

        # Replace the handler with our custom implementation that protects OAuth fields
        from solnlib.splunkenv import get_splunkd_uri

        def get_splunkd_endpoint():
            if os.environ.get("SPLUNKD_URI"):
                return os.environ["SPLUNKD_URI"]
            else:
                splunkd_uri = get_splunkd_uri()
                os.environ["SPLUNKD_URI"] = splunkd_uri
                return splunkd_uri

        self.handler = Analyst1AccountRestHandler(
            get_splunkd_endpoint(),
            self.getSessionKey(),
            self.endpoint,
        )

    def _strip_whitespace_from_credentials(self):
        """
        Strip leading/trailing whitespace from credential fields before saving.

        This prevents API failures caused by copy/paste including whitespace.
        Only strips specific credential fields, not account names or descriptions.

        Note: Must modify self.payload (not self.callerArgs.data) because the UCC
        framework converts callerArgs.data to self.payload in __init__ before
        handleCreate/handleEdit runs. self.payload is a simple dict with direct
        values, not a list like callerArgs.data.
        """
        account_name = self.callerArgs.id
        for field_name in self.STRIP_WHITESPACE_FIELDS:
            if field_name in self.payload:
                value = self.payload[field_name]
                if value:
                    stripped_value = value.strip()
                    if stripped_value != value:
                        logger.debug(
                            f"[Account] Stripped whitespace from {field_name} for '{account_name}'"
                        )
                        self.payload[field_name] = stripped_value

    def _ensure_oauth_fields_exist(self):
        """
        Ensure OAuth accounts have all required encrypted fields in payload.

        CRITICAL FIX: This bypasses the CustomHookMixin mechanism which fails due to
        Python module caching. When another TA loads splunktaucclib first without
        a custom_hook_mixin.py, the module gets cached with BaseHookMixin, and our
        CustomHookMixin never fires.

        OAuth accounts don't use the 'password' field, but UCC's credential handler
        expects ALL encrypted fields defined in the schema to exist in credential
        storage. Without this fix, UCC only stores fields present in the payload,
        causing KeyError: 'password' when retrieving the account later.

        This method injects password="" into the payload BEFORE UCC processes it,
        ensuring credential entries are created in /storage/passwords.

        Note: oauth_token_data is stored in a separate realm (OAUTH_TOKEN_REALM)
        and is not managed through UCC's credential handling.
        """
        account_name = self.callerArgs.id
        try:
            auth_type = self.payload.get("auth_type", "basic")

            if auth_type == "oauth":
                # Ensure password field exists (OAuth accounts don't use it, but UCC expects it)
                # Use "__PLACEHOLDER__" - a non-empty string that UCC will store
                if not self.payload.get("password"):
                    self.payload["password"] = "__PLACEHOLDER__"
                    logger.info(
                        f"account_name={account_name} | action=ensure_oauth_fields | "
                        f"message=Added_password_placeholder_for_OAuth_account | "
                        f"reason=Prevents_KeyError_during_account_retrieval"
                    )
        except Exception as e:
            logger.warning(
                f"account_name={account_name} | action=ensure_oauth_fields | "
                f"message=Failed_to_ensure_oauth_fields | error={e} | "
                f"impact=May_cause_KeyError_on_retrieval"
            )

    def _validate_required_fields(self):
        """
        Validate auth-type-specific required fields.

        UCC field validators only run when fields have values. Since client_secret
        has required=False (to support basic auth), we must validate OAuth-required
        fields explicitly in the handler before UCC processing.
        """
        auth_type = self.payload.get("auth_type", "basic")

        if auth_type == "oauth":
            client_id = (self.payload.get("client_id") or "").strip()
            client_secret = (self.payload.get("client_secret") or "").strip()

            if not client_id or not client_secret:
                raise RestError(
                    400,
                    "Client ID and Client Secret are required for OAuth authentication"
                )
        elif auth_type == "basic":
            username = (self.payload.get("username") or "").strip()
            password = (self.payload.get("password") or "").strip()

            if not username or not password:
                raise RestError(
                    400,
                    "Username and Password are required for basic authentication"
                )

    def handleCreate(self, conf_info):
        """
        Handles the create operation - passes through to parent handler.

        OAuth token generation is handled by the validator (AccountValidator),
        not in the handler. This ensures proper separation of concerns.
        """
        self._validate_required_fields()
        self._ensure_oauth_fields_exist()
        self._strip_whitespace_from_credentials()
        return super().handleCreate(conf_info)

    def handleEdit(self, conf_info):
        """
        Handles the edit operation - passes through to parent handler.

        OAuth token generation is handled by the validator (AccountValidator),
        not in the handler. This ensures proper separation of concerns.
        """
        self._validate_required_fields()
        self._ensure_oauth_fields_exist()
        self._strip_whitespace_from_credentials()
        return super().handleEdit(conf_info)

    def handleList(self, conf_info):
        """
        Handles the list operation - runs migrations first, then parent handler.

        The migration system cleans up legacy data and performs other
        maintenance tasks. Migrations are coordinated across SHC nodes
        using distributed locking.

        Migration characteristics:
        - App-scoped migrations run on SHC captain only (data replicates to members)
        - Node-scoped migrations run on each node independently
        - Idempotent (safe to run multiple times)
        - Fail-safe (KV Store errors skip migrations, don't block account list)
        """
        try:
            from migration.migration_manager import run_migration_check_safe
            session_key = self.getSessionKey()
            run_migration_check_safe(session_key)
        except ImportError:
            pass  # Migration module not available

        # Call parent's handleList (which runs the standard AOB migrations)
        return super().handleList(conf_info)

    def _revoke_oauth_token_if_needed(self, account_name, account_stanza, session_key):
        """
        Attempt to revoke OAuth token if the account is OAuth-enabled and has a valid token.

        Conditions for revocation:
        1. auth_type == "oauth"
        2. Token exists in OAUTH_TOKEN_REALM and contains an access_token
        3. token hasn't expired yet (token_expiry > current time)

        This method NEVER blocks account deletion - failures are logged as warnings.

        Args:
            account_name: Name of the account being deleted
            account_stanza: Account configuration dictionary
            session_key: Splunk session key
        """
        handler_logger = get_logger("ta_analyst1_rest_handler")

        try:
            # Condition 1: Check if account uses OAuth authentication
            auth_type = account_stanza.get("auth_type", "basic")
            if auth_type != "oauth":
                handler_logger.debug(
                    f"account_name={account_name} | message=oauth_revocation_skipped | "
                    f"Skipping OAuth revocation - auth_type is '{auth_type}', not 'oauth'"
                )
                return

            # Condition 2: Read token from OAUTH_TOKEN_REALM (separate from account credentials)
            adapter = SplunkServiceAdapter.from_session_key(session_key)
            token_data = adapter.ta_config.get_oauth_token(account_name)

            if not token_data:
                handler_logger.debug(
                    f"account_name={account_name} | message=oauth_revocation_skipped | "
                    f"Skipping OAuth revocation - no token found in OAuth realm"
                )
                return

            access_token = token_data.get("access_token")
            if not access_token:
                handler_logger.debug(
                    f"account_name={account_name} | message=oauth_revocation_skipped | "
                    f"Skipping OAuth revocation - no access_token in token data"
                )
                return

            # Condition 3: Check if token hasn't expired
            token_expiry = token_data.get("token_expiry", 0)
            current_time = time.time()

            if current_time >= token_expiry:
                handler_logger.debug(
                    f"account_name={account_name} | message=oauth_revocation_skipped | "
                    f"Skipping OAuth revocation - token has already expired "
                    f"(expiry={token_expiry}, current={current_time})"
                )
                return

            # All conditions met - attempt revocation
            handler_logger.info(
                f"account_name={account_name} | message=oauth_revocation_starting | "
                f"Attempting to revoke OAuth token before account deletion"
            )

            # Build config for Analyst1OAuth - must include 'name' key
            oauth_config = dict(account_stanza)
            oauth_config["name"] = account_name

            # Add proxy settings
            oauth_config["proxy"] = get_proxy_info(session_key)

            oauth_helper = Analyst1OAuth(oauth_config, session_key)
            revoked = oauth_helper.revoke_token(access_token=access_token)

            if revoked:
                handler_logger.info(
                    f"account_name={account_name} | message=oauth_revocation_success | "
                    f"Successfully revoked OAuth token before account deletion"
                )
            else:
                handler_logger.warning(
                    f"account_name={account_name} | message=oauth_revocation_partial | "
                    f"OAuth token revocation returned False (server-side may have failed). "
                    f"Proceeding with account deletion."
                )

        except Exception as e:
            # CRITICAL: Never block account deletion due to revocation failure
            handler_logger.warning(
                f"account_name={account_name} | message=oauth_revocation_error | "
                f"OAuth token revocation failed: {e}. Proceeding with account deletion."
            )

    def handleRemove(self, conf_info):
        """
        Handles the delete operation
        :param conf_info: Default parameter generated by AOB which is used to pass the response
        """
        account_stanza_name = self.callerArgs.id
        session_key = self.getSessionKey()
        handler_logger = get_logger("ta_analyst1_rest_handler")
        try:
            account_stanza = get_conf_file(
                file="ta_analyst1_account", stanza=account_stanza_name, session_key=session_key
            )

            # Revoke OAuth token if this is an OAuth account with a valid token
            self._revoke_oauth_token_if_needed(account_stanza_name, account_stanza, session_key)

            # Clean up OAuth token from the separate OAuth token realm
            self._cleanup_oauth_token_realm(account_stanza_name, session_key)

            if is_true(account_stanza.get("use_ca_cert", False)):
                cert_file_name = account_stanza.get("copy_account_name")
                cert_file_loc = CERT_FILE_LOC.format(cert_name=cert_file_name)
                if os.path.exists(cert_file_loc):
                    os.remove(cert_file_loc)
                    handler_logger.info(
                        "account_name={} | message=CA_cert_deleted_successfully | CA cert deleted successfully "
                        "for the Account: {}".format(account_stanza_name, account_stanza_name)
                    )
        except Exception:
            handler_logger.error(
                "account_name={} | message=CA_cert_deletion_error | Error occurred while deleting CA cert."
                " Error: {}".format(account_stanza_name, traceback.format_exc())
            )
        finally:
            super(CustomConfigMigrationHandler, self).handleRemove(conf_info)

    def _cleanup_oauth_token_realm(self, account_name, session_key):
        """
        Clean up OAuth token from the separate OAuth token realm during account deletion.

        This method removes the stored OAuth token from the dedicated OAuth token realm
        using TAConfigOperations. Errors are logged but don't fail the account deletion.

        Args:
            account_name: Name of the account being deleted
            session_key: Splunk session key
        """
        handler_logger = get_logger("ta_analyst1_rest_handler")
        try:
            adapter = SplunkServiceAdapter.from_session_key(session_key)
            deleted = adapter.ta_config.delete_oauth_token(account_name)

            if deleted:
                handler_logger.info(
                    f"account_name={account_name} | message=oauth_token_realm_cleanup_success | "
                    f"Successfully deleted OAuth token from separate realm"
                )
            else:
                handler_logger.debug(
                    f"account_name={account_name} | message=oauth_token_realm_cleanup_not_found | "
                    f"No OAuth token found in separate realm (may not be an OAuth account)"
                )

        except Exception as e:
            # Log error but don't fail account deletion
            handler_logger.warning(
                f"account_name={account_name} | message=oauth_token_realm_cleanup_error | "
                f"Failed to clean up OAuth token from separate realm: {e}. "
                f"This is non-critical and won't affect account deletion."
            )


fields = [
    field.RestField(
        "copy_account_name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=50,
        ),
    ),
    field.RestField(
        "server_address",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=200,
        ),
    ),
    field.RestField(
        "auth_type",
        required=False,
        encrypted=False,
        default="basic",
        validator=validator.String(
            min_len=1,
            max_len=20,
        ),
    ),
    field.RestField(
        "username",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=200,
        ),
    ),
    field.RestField(
        "password",
        required=False,
        encrypted=True,
        default=None,
        validator=AccountValidator(),
    ),
    field.RestField(
        "client_id",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=200,
        ),
    ),
    field.RestField(
        "client_secret",
        required=False,
        encrypted=True,
        default=None,
        validator=AccountValidator(),
    ),
    field.RestField(
        "access_token",
        required=False,
        encrypted=True,
        default=None,
        validator=None,
    ),
    field.RestField(
        "token_expiry",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "use_ca_cert",
        required=False,
        encrypted=False,
        default=False,
        validator=None,
    ),
    field.RestField(
        "custom_certificate",
        required=False,
        encrypted=False,
        default="",
        validator=None,
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    "ta_analyst1_account",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )
