"""
Centralized OAuth Token Endpoint

REST handler that serves as the single point of control for all OAuth token operations.
This solves token thrashing on Search Head Clusters (SHC) where multiple members can
generate/revoke tokens, invalidating each other's tokens due to Analyst1's one-token-per-client_id constraint.

Modes:
    - get_or_generate (default): Return valid token if exists, generate if expired/missing
    - validate_and_save: Validate credentials and save token (for account creation)
    - force_refresh: Always generate new token, revoke existing first
    - revoke: Revoke token and clear local storage without generating new token

Usage:
    POST /servicesNS/nobody/TA-Analyst1/ta_analyst1_oauth_token
    Body: account_name=<name>&mode=<mode>&[client_id=...&client_secret=...&server_address=...]
"""

from __future__ import annotations

import ta_analyst1_declare  # noqa: F401
import json
import re
import socket
import time
from typing import Any, Dict, Optional

import splunk.admin as admin
from analyst1_logging import get_logger
from splunk_client.splunk_service_adapter import (
    SplunkServiceAdapter,
    KVStoreError,
    TAConfigOperations,
)

# Import OAuth helper and locking functions
from ta_analyst1.analyst1_oauth_helper import (
    Analyst1OAuth,
    OAuthError,
    TOKEN_REFRESH_BUFFER_SECONDS,
)

logger = get_logger("ta_analyst1_oauth_endpoint")

# Error codes for structured error responses
ERROR_CODES = {
    "INVALID_CREDENTIALS": "INVALID_CREDENTIALS",
    "ACCOUNT_NOT_FOUND": "ACCOUNT_NOT_FOUND",
    "LOCK_ACQUISITION_FAILED": "LOCK_ACQUISITION_FAILED",
    "LOCK_TIMEOUT": "LOCK_TIMEOUT",
    "TOKEN_GENERATION_FAILED": "TOKEN_GENERATION_FAILED",
    "INVALID_MODE": "INVALID_MODE",
    "MISSING_REQUIRED_PARAM": "MISSING_REQUIRED_PARAM",
    "INTERNAL_ERROR": "INTERNAL_ERROR",
}

# Entry-point lock configuration
ENTRANT_LOCK_COLLECTION = "analyst1_oauth_locks"
ENTRANT_LOCK_TIMEOUT_SECONDS = 60  # Lock validity period
ENTRANT_LOCK_WAIT_INTERVAL = 0.5  # Polling interval for lock acquisition
ENTRANT_LOCK_MAX_WAIT_SECONDS = 60  # Maximum time to wait for lock (matches TTL)

# Time to wait for password.conf replication across SHC nodes
# Based on: push to captain (~2s) + member poll interval (~5s) + buffer (~3s)
SHC_REPLICATION_WAIT_SECONDS = 10


def _sanitize_token_from_message(message: str) -> str:
    """
    Remove any tokens from error messages to prevent credential leakage.

    Args:
        message: Error message that may contain tokens

    Returns:
        Sanitized message with tokens redacted
    """
    if not message:
        return message

    # Redact JWT tokens (three base64 segments separated by dots)
    sanitized = re.sub(
        r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',
        '[REDACTED_JWT]',
        message
    )
    # Redact other long base64-like strings (potential tokens)
    sanitized = re.sub(r'[A-Za-z0-9+/=]{60,}', '[REDACTED_TOKEN]', sanitized)

    return sanitized


class OAuthTokenHandler(admin.MConfigHandler):
    """
    REST handler for centralized OAuth token operations.

    Provides a single endpoint for all OAuth token management to prevent
    token thrashing on Search Head Clusters.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Track whether we generated a new token (for SHC replication wait)
        self._new_token_generated = False

    def setup(self):
        """Set up supported arguments for the endpoint."""
        # Required arguments
        self.supportedArgs.addReqArg("account_name")

        # Optional arguments
        self.supportedArgs.addOptArg("mode")  # get_or_generate, validate_and_save, force_refresh, revoke

        # For validate_and_save mode - credentials passed explicitly (not from disk)
        self.supportedArgs.addOptArg("client_id")
        self.supportedArgs.addOptArg("client_secret")
        self.supportedArgs.addOptArg("server_address")
        self.supportedArgs.addOptArg("use_ca_cert")
        self.supportedArgs.addOptArg("custom_certificate")

        # For force_refresh mode - compare-and-swap to prevent ping-pong
        self.supportedArgs.addOptArg("expected_stale_token")

    def handleList(self, confInfo):
        """
        Handle GET request - not supported, redirect to POST.

        GET is intentionally not supported because token operations should be explicit.
        """
        # Return empty response for GET - actual work is done via POST
        confInfo["status"]["success"] = "false"
        confInfo["status"]["error"] = "GET not supported. Use POST."

    def handleCreate(self, confInfo):
        """
        Handle POST request - main token operation entry point.

        Dispatches to appropriate handler based on mode parameter.
        Uses entry-point distributed lock to serialize ALL token operations per account.
        """
        session_key = self.getSessionKey()

        # Create single adapter for reuse across all lock operations
        # This avoids creating 4 separate adapters (each triggering network validation)
        adapter = SplunkServiceAdapter.from_session_key(session_key)

        # Extract arguments
        account_name = self._get_arg("account_name")
        mode = self._get_arg("mode", default="get_or_generate")

        logger.info(
            f"[OAuth Endpoint] Request received: account_name={account_name}, mode={mode}"
        )

        # Validate mode
        valid_modes = ["get_or_generate", "validate_and_save", "force_refresh", "revoke"]
        if mode not in valid_modes:
            error_msg = f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
            logger.error(f"[OAuth Endpoint] {error_msg}")
            self._set_response(
                confInfo, success=False, error=error_msg,
                error_code=ERROR_CODES["INVALID_MODE"])
            return

        # Acquire entry-point lock for ALL operations to prevent race conditions
        lock_acquired = False
        try:
            lock_acquired = self._acquire_entrant_lock(account_name, session_key, adapter)
            # Reset flag - will be set True if we generate a new token
            self._new_token_generated = False

            if not lock_acquired:
                error_msg = "Token operation in progress for this account, please retry"
                logger.warning(
                    f"[OAuth Endpoint] Lock acquisition failed for account '{account_name}'"
                )
                self._set_response(
                    confInfo, success=False, error=error_msg,
                    error_code=ERROR_CODES["LOCK_TIMEOUT"])
                return

            # Dispatch to appropriate handler
            if mode == "get_or_generate":
                self._handle_get_or_generate(confInfo, account_name, session_key)
            elif mode == "validate_and_save":
                self._handle_validate_and_save(confInfo, account_name, session_key)
            elif mode == "force_refresh":
                self._handle_force_refresh(confInfo, account_name, session_key)
            elif mode == "revoke":
                self._handle_revoke(confInfo, account_name, session_key)

        except Exception as e:
            error_msg = _sanitize_token_from_message(str(e))
            logger.error(
                f"[OAuth Endpoint] Unexpected error for account '{account_name}': {error_msg}",
                exc_info=True
            )
            self._set_response(
                confInfo, success=False, error=error_msg,
                error_code=ERROR_CODES["INTERNAL_ERROR"])
        finally:
            if lock_acquired:
                # Wait for SHC replication if we generated a new token
                if self._new_token_generated:
                    self._wait_for_shc_replication(adapter)
                self._release_entrant_lock(account_name, session_key, adapter)

    def _handle_get_or_generate(self, confInfo, account_name: str, session_key: str):
        """
        Handle get_or_generate mode.

        Read fresh config, check for valid stored token, generate if needed.
        """
        logger.debug(f"[OAuth Endpoint] get_or_generate mode for account '{account_name}'")

        # Read fresh config from disk
        account_config = self._read_fresh_config(account_name, session_key)
        if account_config is None:
            error_msg = f"Account '{account_name}' not found"
            logger.error(f"[OAuth Endpoint] {error_msg}")
            self._set_response(
                confInfo, success=False, error=error_msg,
                error_code=ERROR_CODES["ACCOUNT_NOT_FOUND"])
            return

        # Check for existing valid token
        token_data = self._get_token_data_from_config(account_config)

        if token_data and self._is_token_valid(token_data):
            # Token is valid and not expiring - return it
            expires_in = int(token_data["token_expiry"] - time.time())
            logger.debug(
                f"[OAuth Endpoint] Returning existing valid token for '{account_name}' "
                f"(expires in {expires_in}s)"
            )
            self._set_response(
                confInfo,
                success=True,
                access_token=token_data["access_token"],
                expires_in=expires_in,
                message="Token retrieved successfully"
            )
            return

        # Token is missing, expired, or expiring soon - generate new one
        logger.debug(
            f"[OAuth Endpoint] Generating new token for '{account_name}' "
            f"(token {'missing' if not token_data else 'expired/expiring'})"
        )

        self._generate_and_save_token(confInfo, account_config, session_key, account_name)

    def _handle_validate_and_save(self, confInfo, account_name: str, session_key: str):
        """
        Handle validate_and_save mode for credential validation during account creation.

        Uses explicitly passed credentials (NOT from disk).
        Handles one-token constraint based on client_id comparison.
        Generates token and saves it to OAUTH_TOKEN_REALM so the account is
        ready to use immediately after creation (avoids wasteful generate-revoke-generate cycle).
        """
        logger.debug(f"[OAuth Endpoint] validate_and_save mode for account '{account_name}'")

        # Get explicitly passed credentials
        client_id = self._get_arg("client_id")
        client_secret = self._get_arg("client_secret")
        server_address = self._get_arg("server_address")
        use_ca_cert = self._get_arg("use_ca_cert")
        custom_certificate = self._get_arg("custom_certificate")

        # Strip whitespace from credentials to prevent "API key does not exist" errors
        # caused by copy/paste including leading/trailing whitespace
        if client_id:
            stripped_client_id = client_id.strip()
            if stripped_client_id != client_id:
                logger.debug(
                    f"[OAuth Endpoint] Stripped whitespace from client_id for '{account_name}'"
                )
            client_id = stripped_client_id

        if client_secret:
            stripped_client_secret = client_secret.strip()
            if stripped_client_secret != client_secret:
                logger.debug(
                    f"[OAuth Endpoint] Stripped whitespace from client_secret for '{account_name}'"
                )
            client_secret = stripped_client_secret

        if server_address:
            stripped_server_address = server_address.strip()
            if stripped_server_address != server_address:
                logger.debug(
                    f"[OAuth Endpoint] Stripped whitespace from server_address for '{account_name}'"
                )
            server_address = stripped_server_address

        # Validate required parameters for validate_and_save mode
        if not client_id or not client_secret or not server_address:
            error_msg = "client_id, client_secret, and server_address are required for validate_and_save mode"
            logger.error(f"[OAuth Endpoint] {error_msg}")
            self._set_response(
                confInfo, success=False, error=error_msg,
                error_code=ERROR_CODES["MISSING_REQUIRED_PARAM"])
            return

        # Get proxy settings from ta_analyst1_settings
        proxy_settings = self._get_proxy_settings(session_key)

        # Build test config using passed credentials
        test_config = {
            "name": account_name,
            "client_id": client_id,
            "client_secret": client_secret,
            "server_address": server_address,
            "use_ca_cert": use_ca_cert,
            "custom_certificate": custom_certificate,
            "proxy": proxy_settings,
        }

        # Read stored account config (if exists) for client_id comparison
        stored_config = self._read_fresh_config(account_name, session_key)
        stored_client_id = stored_config.get("client_id") if stored_config else None

        # Handle one-token constraint based on client_id comparison
        if stored_config and stored_client_id == client_id:
            # SAME client_id - must revoke stored token first (one-token constraint)
            logger.debug(
                f"[OAuth Endpoint] Same client_id detected for '{account_name}', "
                "checking if stored token needs revocation"
            )
            token_data = self._get_token_data_from_config(stored_config)
            if token_data and "access_token" in token_data:
                # Check if token is already expired - no need to revoke expired tokens
                token_expiry = token_data.get("token_expiry", 0)
                current_time = time.time()
                if current_time >= token_expiry:
                    logger.debug(
                        f"[OAuth Endpoint] Stored token for '{account_name}' has already expired, "
                        "skipping revocation"
                    )
                else:
                    # Token is still active - MUST revoke it before generating new token
                    # Due to one-token-per-client constraint, failing to revoke here would
                    # cause the new test token to invalidate the stored token, leading to
                    # token thrashing. This is a critical error - do NOT proceed.
                    try:
                        stored_oauth_helper = Analyst1OAuth(stored_config, session_key)
                        stored_oauth_helper.revoke_token(access_token=token_data["access_token"])
                        logger.debug(f"[OAuth Endpoint] Revoked stored token for '{account_name}'")
                    except Exception as e:
                        sanitized_error = _sanitize_token_from_message(str(e))
                        error_msg = (
                            f"Failed to revoke existing token for '{account_name}': {sanitized_error}. "
                            "Cannot validate credentials without first revoking the active token "
                            "(one-token-per-client constraint)."
                        )
                        logger.error(f"[OAuth Endpoint] {error_msg}")
                        self._set_response(
                            confInfo, success=False, error=error_msg,
                            error_code=ERROR_CODES["TOKEN_GENERATION_FAILED"])
                        return
        elif stored_config and stored_client_id != client_id:
            # DIFFERENT client_id - no revocation needed (different OAuth client)
            logger.debug(
                f"[OAuth Endpoint] Different client_id for '{account_name}' "
                f"(stored: {stored_client_id[:8] if stored_client_id else 'none'}..., "
                f"new: {client_id[:8]}...), skipping stored token revocation"
            )
        else:
            # New account - no stored token to revoke
            logger.debug(f"[OAuth Endpoint] New account '{account_name}', no stored token to revoke")

        # Generate and save token with NEW credentials
        # Token is saved so the account is ready to use immediately after creation,
        # avoiding a wasteful generate-revoke-generate cycle
        try:
            test_oauth_helper = Analyst1OAuth(test_config, session_key)
            success, expires_in, access_token, error_msg = test_oauth_helper.generate_oauth_access_token(
                save_token=True,  # Save token so account is ready to use immediately
                force_revoke=True  # Always try to revoke - handles orphaned tokens from failed revocations
            )

            if not success or not access_token:
                sanitized_error = _sanitize_token_from_message(error_msg or "Token generation failed")
                logger.error(
                    f"[OAuth Endpoint] Token generation failed for '{account_name}': "
                    f"{sanitized_error}"
                )
                self._set_response(
                    confInfo, success=False, error=sanitized_error,
                    error_code=ERROR_CODES["INVALID_CREDENTIALS"])
                return

            # Mark that we generated a new token (for SHC replication wait)
            self._new_token_generated = True

            logger.info(
                f"[OAuth Endpoint] Credential validation successful for '{account_name}', "
                f"token saved (expires in {expires_in}s)"
            )
            self._set_response(
                confInfo,
                success=True,
                access_token=None,  # Don't return token in response (validation only)
                expires_in=None,
                message="Credentials validated successfully"
            )

        except OAuthError as e:
            sanitized_error = _sanitize_token_from_message(str(e))
            logger.error(
                f"[OAuth Endpoint] OAuth error during validate_and_save for '{account_name}': "
                f"{sanitized_error}"
            )
            self._set_response(
                confInfo, success=False, error=sanitized_error,
                error_code=ERROR_CODES["INVALID_CREDENTIALS"])
        except Exception as e:
            sanitized_error = _sanitize_token_from_message(str(e))
            logger.error(
                f"[OAuth Endpoint] Unexpected error during validate_and_save for '{account_name}': "
                f"{sanitized_error}",
                exc_info=True
            )
            self._set_response(
                confInfo, success=False, error=sanitized_error,
                error_code=ERROR_CODES["INTERNAL_ERROR"])

    def _handle_force_refresh(self, confInfo, account_name: str, session_key: str):
        """
        Handle force_refresh mode with compare-and-swap to prevent ping-pong.

        If expected_stale_token is provided, checks if cached token matches.
        If not (another client already refreshed), returns current cached token
        instead of generating a new one. This prevents token refresh ping-pong
        between multiple clients that both receive 401 errors.

        If expected_stale_token is not provided or matches cached token,
        proceeds with normal token generation.
        """
        logger.debug(f"[OAuth Endpoint] force_refresh mode for account '{account_name}'")

        expected_stale_token = self._get_arg("expected_stale_token")

        # Read fresh config from disk
        account_config = self._read_fresh_config(account_name, session_key)
        if account_config is None:
            error_msg = f"Account '{account_name}' not found"
            logger.error(f"[OAuth Endpoint] {error_msg}")
            self._set_response(
                confInfo, success=False, error=error_msg,
                error_code=ERROR_CODES["ACCOUNT_NOT_FOUND"])
            return

        # Compare-and-swap: If expected_stale_token provided, check if someone else already refreshed
        if expected_stale_token:
            token_data = self._get_token_data_from_config(account_config)
            if token_data:
                current_token = token_data.get("access_token")
                if current_token and current_token != expected_stale_token:
                    # Someone else already refreshed - return current token instead
                    token_expiry = token_data.get("token_expiry", 0)
                    current_time = time.time()
                    expires_in = max(0, int(token_expiry - current_time))
                    logger.info(
                        f"[OAuth Endpoint] CAS: Token already refreshed by another client for '{account_name}', "
                        f"returning existing token instead of generating new one"
                    )
                    self._set_response(
                        confInfo,
                        success=True,
                        access_token=current_token,
                        expires_in=expires_in,
                        message="Token already refreshed by another client"
                    )
                    return

        # Generate new token (OAuth helper will handle revocation with force_revoke=True)
        self._generate_and_save_token(confInfo, account_config, session_key, account_name)

    def _handle_revoke(self, confInfo, account_name: str, session_key: str):
        """
        Handle revoke mode - revoke token and clear local storage without generating new token.

        Used for cleanup operations where we want to invalidate a token
        without immediately replacing it.
        """
        logger.debug(f"[OAuth Endpoint] revoke mode for account '{account_name}'")

        try:
            adapter = SplunkServiceAdapter.from_session_key(session_key)

            # Read account config
            account_config = self._read_fresh_config(account_name, session_key)
            if account_config is None:
                error_msg = f"Account '{account_name}' not found"
                logger.error(f"[OAuth Endpoint] {error_msg}")
                self._set_response(
                    confInfo, success=False, error=error_msg,
                    error_code=ERROR_CODES["ACCOUNT_NOT_FOUND"])
                return

            # Get stored token data
            token_data = adapter.ta_config.get_oauth_token(account_name)

            if not token_data or not token_data.get("access_token"):
                logger.info(f"[OAuth Endpoint] No active token to revoke for account '{account_name}'")
                self._set_response(
                    confInfo,
                    success=True,
                    message=f"No active token to revoke for account '{account_name}'"
                )
                return

            # Revoke on Analyst1 server using Analyst1OAuth helper
            server_revoked = False
            try:
                oauth_helper = Analyst1OAuth(account_config, session_key)
                server_revoked = oauth_helper.revoke_token(access_token=token_data["access_token"])
            except Exception as e:
                sanitized_error = _sanitize_token_from_message(str(e))
                logger.warning(
                    f"[OAuth Endpoint] Server-side revocation failed for '{account_name}': {sanitized_error}. "
                    "Continuing with local cleanup."
                )

            # Clear from local storage regardless of server result
            adapter.ta_config.delete_oauth_token(account_name)

            logger.info(f"[OAuth Endpoint] Token revoked for account '{account_name}' (server_revoked={server_revoked})")
            self._set_response(
                confInfo,
                success=True,
                message=f"Token revoked for account '{account_name}'"
            )

        except Exception as e:
            sanitized_error = _sanitize_token_from_message(str(e))
            logger.error(
                f"[OAuth Endpoint] Error revoking token for '{account_name}': {sanitized_error}",
                exc_info=True
            )
            self._set_response(
                confInfo, success=False, error=sanitized_error,
                error_code=ERROR_CODES["INTERNAL_ERROR"])

    def _generate_and_save_token(
        self,
        confInfo,
        account_config: Dict[str, Any],
        session_key: str,
        account_name: str
    ):
        """
        Generate a new OAuth token and save it.

        Common logic for get_or_generate and force_refresh modes.
        """
        try:
            oauth_helper = Analyst1OAuth(account_config, session_key)
            success, expires_in, access_token, error_msg = oauth_helper.generate_oauth_access_token(
                save_token=True,
                force_revoke=True
            )

            if success and access_token:
                # Mark that we generated a new token (for SHC replication wait)
                self._new_token_generated = True
                logger.info(
                    f"[OAuth Endpoint] Token generated and saved for '{account_name}' "
                    f"(expires in {expires_in}s)"
                )
                self._set_response(
                    confInfo,
                    success=True,
                    access_token=access_token,
                    expires_in=expires_in,
                    message="Token generated successfully"
                )
            else:
                sanitized_error = _sanitize_token_from_message(error_msg or "Token generation failed")
                logger.error(
                    f"[OAuth Endpoint] Token generation failed for '{account_name}': "
                    f"{sanitized_error}"
                )
                self._set_response(
                    confInfo, success=False, error=sanitized_error,
                    error_code=ERROR_CODES["TOKEN_GENERATION_FAILED"])

        except OAuthError as e:
            sanitized_error = _sanitize_token_from_message(str(e))
            logger.error(
                f"[OAuth Endpoint] OAuth error for '{account_name}': {sanitized_error}"
            )
            self._set_response(
                confInfo, success=False, error=sanitized_error,
                error_code=ERROR_CODES["TOKEN_GENERATION_FAILED"])
        except Exception as e:
            sanitized_error = _sanitize_token_from_message(str(e))
            logger.error(
                f"[OAuth Endpoint] Unexpected error for '{account_name}': {sanitized_error}",
                exc_info=True
            )
            self._set_response(
                confInfo, success=False, error=sanitized_error,
                error_code=ERROR_CODES["INTERNAL_ERROR"])

    def _read_fresh_config(self, account_name: str, session_key: str) -> Optional[Dict[str, Any]]:
        """
        Read account configuration using splunklib (no solnlib).

        Reads:
        1. Non-encrypted fields from ta_analyst1_account.conf via splunklib
        2. Encrypted fields from storage/passwords via TAConfigOperations
        3. OAuth token from separate realm via TAConfigOperations
        4. Merges them together

        Returns:
            Account configuration dict with decrypted credentials, or None if not found
        """
        try:
            adapter = SplunkServiceAdapter.from_session_key(session_key)

            # 1. Read conf file (non-encrypted fields)
            conf_data = adapter.config.get_stanza("ta_analyst1_account", account_name)
            if not conf_data:
                logger.debug(f"[OAuth Endpoint] Account '{account_name}' not found in conf")
                return None

            # 2. Read credentials (encrypted fields) using TAConfigOperations
            cred_data = adapter.ta_config.get_account_credentials(account_name)

            if cred_data:
                # Merge encrypted fields into config
                # These fields are stored encrypted: password, client_secret
                # Also check for access_token which may exist in older credential blobs
                for key in ["password", "client_secret", "access_token"]:
                    if key in cred_data:
                        conf_data[key] = cred_data[key]
            else:
                # No credentials found - attempt migration for legacy accounts
                logger.info(
                    f"[OAuth Endpoint] No credentials found for '{account_name}', "
                    "attempting migration for legacy account"
                )
                if self._migrate_legacy_oauth_account(account_name, session_key):
                    # Migration created credentials - try reading them again
                    cred_data = adapter.ta_config.get_account_credentials(account_name)
                    if cred_data:
                        for key in ["password", "client_secret", "access_token"]:
                            if key in cred_data:
                                conf_data[key] = cred_data[key]

            # 3. Read OAuth token from separate realm using TAConfigOperations
            token_data = adapter.ta_config.get_oauth_token(account_name)
            if token_data:
                # Store as JSON string to match expected format
                conf_data["oauth_token_data"] = json.dumps(token_data)

            # Ensure account name is in the config
            if "name" not in conf_data:
                conf_data["name"] = account_name

            # Add proxy settings
            proxy_settings = self._get_proxy_settings(session_key)
            if proxy_settings:
                conf_data["proxy"] = proxy_settings

            return conf_data

        except Exception as e:
            logger.error(
                f"[OAuth Endpoint] Error reading config for '{account_name}': {e}",
                exc_info=True
            )
            return None

    def _migrate_legacy_oauth_account(self, account_name: str, session_key: str) -> bool:
        """
        Migrate a legacy OAuth account by adding oauth_token_data to passwords.conf.

        Legacy OAuth accounts created before oauth_token_data was added as an encrypted
        field will have oauth_token_data marked as encrypted in the schema but missing
        from passwords.conf. This causes KeyError when conf_manager tries to decrypt it.

        CRITICAL: This method uses SplunkServiceAdapter.credentials with direct REST API
        which handles create-or-update atomically (no delete-then-create pattern).
        This approach:
        1. Does NOT read encrypted fields (avoids "******" masking issue)
        2. Does NOT rewrite existing credentials (preserves client_secret, password)
        3. Only adds the missing oauth_token_data field

        Args:
            account_name: Name of the account to migrate
            session_key: Splunk session key

        Returns:
            True if migration successful, False otherwise
        """
        try:
            # Use SplunkServiceAdapter.credentials for proper credential access
            # This returns DECRYPTED values, not masked "******" values
            adapter = SplunkServiceAdapter.from_session_key(session_key)

            # Get existing credential data for this account using TAConfigOperations realm constant
            # This returns the raw JSON blob from passwords.conf (decrypted)
            existing_creds = adapter.credentials.get_credential_data(
                TAConfigOperations.ACCOUNT_REALM, account_name
            )

            if not existing_creds:
                # New account - create with placeholder using atomic set_credential_data
                adapter.credentials.set_credential_data(
                    TAConfigOperations.ACCOUNT_REALM,
                    account_name,
                    json.dumps({
                        "password": "__PLACEHOLDER__",
                        "client_secret": "",
                        "oauth_token_data": "{}"
                    })
                )
                logger.info(
                    f"[OAuth Endpoint] Created oauth_token_data entry for new account '{account_name}'"
                )
                return True

            # Existing credentials found - parse and add oauth_token_data
            try:
                cred_dict = json.loads(existing_creds)
            except json.JSONDecodeError:
                # Not valid JSON - create fresh using atomic set_credential_data
                adapter.credentials.set_credential_data(
                    TAConfigOperations.ACCOUNT_REALM,
                    account_name,
                    json.dumps({
                        "password": "__PLACEHOLDER__",
                        "client_secret": "",
                        "oauth_token_data": "{}"
                    })
                )
                logger.info(
                    f"[OAuth Endpoint] Updated oauth_token_data for account '{account_name}' (non-JSON)"
                )
                return True

            # Add oauth_token_data if missing
            if "oauth_token_data" not in cred_dict:
                cred_dict["oauth_token_data"] = "{}"
                # Use atomic set_credential_data (handles create-or-update internally)
                adapter.credentials.set_credential_data(
                    TAConfigOperations.ACCOUNT_REALM,
                    account_name,
                    json.dumps(cred_dict)
                )
                logger.info(
                    f"[OAuth Endpoint] Successfully migrated legacy OAuth account '{account_name}' - "
                    f"added oauth_token_data to passwords.conf"
                )
            else:
                logger.debug(
                    f"[OAuth Endpoint] Account '{account_name}' already has oauth_token_data, "
                    f"no migration needed"
                )

            return True

        except Exception as e:
            logger.error(
                f"[OAuth Endpoint] Migration failed for '{account_name}': {e}",
                exc_info=True
            )
            return False

    def _get_proxy_settings(self, session_key: str) -> Optional[Dict[str, str]]:
        """
        Get proxy settings from ta_analyst1_settings conf file.

        Returns:
            Proxy dict {"http": "...", "https": "..."} or None
        """
        try:
            # Use the existing get_proxy_info function from conf_helper
            from ta_analyst1.analyst1_helpers.conf_helper import get_proxy_info
            return get_proxy_info(session_key)
        except Exception as e:
            logger.debug(f"[OAuth Endpoint] Failed to get proxy settings: {e}")
            return None

    def _get_token_data_from_config(self, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract token data from account configuration.

        Token data is stored as a JSON blob in oauth_token_data field.

        Returns:
            Token data dict or None if not present/invalid
        """
        oauth_token_data_json = config.get("oauth_token_data")
        if not oauth_token_data_json:
            return None

        try:
            token_data = json.loads(oauth_token_data_json)
            if "access_token" in token_data and "token_expiry" in token_data:
                return token_data
            return None
        except json.JSONDecodeError:
            return None

    def _is_token_valid(self, token_data: Dict[str, Any]) -> bool:
        """
        Check if token is valid and not expiring soon.

        Token is considered valid if it won't expire within TOKEN_REFRESH_BUFFER_SECONDS.

        Returns:
            True if token is valid and has sufficient time remaining
        """
        if not token_data or "token_expiry" not in token_data:
            return False

        try:
            token_expiry = float(token_data["token_expiry"])
            current_time = time.time()

            # Token is valid if it won't expire within the buffer period
            return current_time < (token_expiry - TOKEN_REFRESH_BUFFER_SECONDS)
        except (ValueError, TypeError):
            return False
    def _get_arg(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get argument from request, handling list format.

        Args:
            name: Argument name
            default: Default value if not present

        Returns:
            Argument value or default
        """
        value = self.callerArgs.get(name)
        if value is None:
            return default
        if isinstance(value, list):
            return value[0] if value else default
        return value

    def _set_response(
        self,
        confInfo,
        success: bool,
        access_token: Optional[str] = None,
        expires_in: Optional[int] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        """
        Set the REST response in a consistent format.

        Response format:
        {
            "success": bool,
            "access_token": str|null,
            "expires_in": int|null,
            "message": str|null,
            "error": str|null,
            "error_code": str|null
        }
        """
        # Use a single status key to store the response
        confInfo["status"]["success"] = "true" if success else "false"

        if access_token:
            confInfo["status"]["access_token"] = access_token
        if expires_in is not None:
            confInfo["status"]["expires_in"] = str(expires_in)
        if message:
            confInfo["status"]["message"] = message
        if error:
            confInfo["status"]["error"] = error
        if error_code:
            confInfo["status"]["error_code"] = error_code

    # =========================================================================
    # ENTRY-POINT DISTRIBUTED LOCK METHODS
    # =========================================================================

    def _get_server_guid(self, session_key: str, adapter: SplunkServiceAdapter) -> str:
        """
        Get Splunk server GUID for lock ownership tracking.

        Args:
            session_key: Splunk session key
            adapter: SplunkServiceAdapter instance for Splunk API calls

        Returns:
            Server GUID or fallback identifier
        """
        try:
            response = adapter.service.get("/services/server/info", output_mode="json")
            if response and hasattr(response, 'body'):
                body = response.body.read()
                if isinstance(body, bytes):
                    body = body.decode("utf-8")
                data = json.loads(body)
                if 'entry' in data and len(data['entry']) > 0:
                    guid = data['entry'][0]['content'].get('guid')
                    if guid:
                        return guid
        except Exception as e:
            logger.debug(f"[OAuth Endpoint] Failed to get server GUID: {e}")

        # Fallback to hostname
        return f"fallback_{socket.gethostname()}"

    def _cleanup_stale_entrant_lock(
        self,
        account_name: str,
        session_key: str,
        adapter: SplunkServiceAdapter,
        max_age: int = ENTRANT_LOCK_TIMEOUT_SECONDS
    ) -> None:
        """
        Clean up expired entry-point locks before acquisition.

        Args:
            account_name: Account name to clean locks for
            session_key: Splunk session key
            adapter: SplunkServiceAdapter instance for Splunk API calls
            max_age: Maximum age in seconds before considering lock expired
        """
        lock_key = f"entrant_lock_{account_name}"

        try:
            lock_data = adapter.kv_store.get(ENTRANT_LOCK_COLLECTION, lock_key)

            if lock_data and isinstance(lock_data, dict):
                acquired_at = lock_data.get('acquired_at', 0)
                age = time.time() - acquired_at

                if age > max_age:
                    logger.debug(
                        f"[OAuth Endpoint] Cleaning up stale entrant lock for '{account_name}' "
                        f"(age={age:.1f}s, max_age={max_age}s)"
                    )
                    adapter.kv_store.delete(ENTRANT_LOCK_COLLECTION, lock_key)
        except KVStoreError as e:
            # Lock may not exist - this is expected
            logger.debug(f"[OAuth Endpoint] Stale lock cleanup check: {e}")
        except Exception as e:
            logger.debug(f"[OAuth Endpoint] Error during stale lock cleanup: {e}")

    def _acquire_entrant_lock(
        self,
        account_name: str,
        session_key: str,
        adapter: SplunkServiceAdapter,
        timeout: int = ENTRANT_LOCK_TIMEOUT_SECONDS
    ) -> bool:
        """
        Acquire distributed entry-point lock for OAuth token operations.

        This lock serializes ALL token operations (get_or_generate, force_refresh,
        validate_and_save) at the REST endpoint level to prevent race conditions where
        concurrent requests could return stale tokens.

        Args:
            account_name: Account name to acquire lock for
            session_key: Splunk session key
            adapter: SplunkServiceAdapter instance for Splunk API calls
            timeout: Lock validity period in seconds (for stale lock cleanup)

        Returns:
            True if lock acquired, False if acquisition failed after retries
        """
        lock_key = f"entrant_lock_{account_name}"
        server_guid = self._get_server_guid(session_key, adapter)

        # Clean up any stale locks first
        self._cleanup_stale_entrant_lock(account_name, session_key, adapter, timeout)

        # Calculate max attempts based on wait time and interval
        max_attempts = int(ENTRANT_LOCK_MAX_WAIT_SECONDS / ENTRANT_LOCK_WAIT_INTERVAL) + 1

        for attempt in range(max_attempts):
            try:
                current_time = time.time()
                lock_data = {
                    "_key": lock_key,
                    "owner_guid": server_guid,
                    "account_name": account_name,
                    "acquired_at": current_time,
                }

                # Try atomic INSERT - will fail with 409 if lock exists
                adapter.kv_store.insert(ENTRANT_LOCK_COLLECTION, lock_data)
                logger.debug(
                    f"[OAuth Endpoint] Acquired entrant lock for '{account_name}' "
                    f"(holder={server_guid})"
                )
                return True

            except KVStoreError as e:
                error_str = str(e)
                if '409' in error_str:
                    # Lock exists - check if it's stale
                    self._cleanup_stale_entrant_lock(account_name, session_key, adapter, timeout)

                    if attempt < max_attempts - 1:
                        logger.debug(
                            f"[OAuth Endpoint] Entrant lock held for '{account_name}', "
                            f"waiting {ENTRANT_LOCK_WAIT_INTERVAL}s (attempt {attempt + 1}/{max_attempts})"
                        )
                        time.sleep(ENTRANT_LOCK_WAIT_INTERVAL)
                    else:
                        logger.warning(
                            f"[OAuth Endpoint] Failed to acquire entrant lock for '{account_name}' "
                            f"after {max_attempts} attempts ({ENTRANT_LOCK_MAX_WAIT_SECONDS}s)"
                        )
                else:
                    logger.warning(
                        f"[OAuth Endpoint] KVStore error acquiring entrant lock: {e}"
                    )
                    # On unexpected KVStore errors, allow operation to proceed (fail open)
                    return True
            except Exception as e:
                error_str = str(e)
                if '409' in error_str:
                    # Same handling as KVStoreError for 409
                    self._cleanup_stale_entrant_lock(account_name, session_key, adapter, timeout)

                    if attempt < max_attempts - 1:
                        logger.debug(
                            f"[OAuth Endpoint] Entrant lock held for '{account_name}', "
                            f"waiting {ENTRANT_LOCK_WAIT_INTERVAL}s (attempt {attempt + 1}/{max_attempts})"
                        )
                        time.sleep(ENTRANT_LOCK_WAIT_INTERVAL)
                    else:
                        logger.warning(
                            f"[OAuth Endpoint] Failed to acquire entrant lock for '{account_name}' "
                            f"after {max_attempts} attempts ({ENTRANT_LOCK_MAX_WAIT_SECONDS}s)"
                        )
                else:
                    logger.warning(
                        f"[OAuth Endpoint] Unexpected error acquiring entrant lock: {e}"
                    )
                    # On unexpected errors, allow operation to proceed (fail open)
                    return True

        return False

    def _wait_for_shc_replication(self, adapter: SplunkServiceAdapter):
        """
        Wait for password.conf to replicate across SHC nodes.

        In SHC environments, configuration changes replicate as follows:
        1. Non-captain member pushes change to captain (~1-2s)
        2. Other members poll captain for changes (~5s interval)

        We hold the entry-point lock during this window to ensure other nodes
        see the updated token before their CAS check runs.

        On standalone instances, this wait is skipped entirely.

        Args:
            adapter: SplunkServiceAdapter instance for checking SHC status
        """
        # Skip wait on standalone instances (includes checking Victoria - which IS SHC)
        if not adapter.cluster.is_shc_enabled():
            logger.debug(
                "[OAuth Endpoint] Standalone instance - skipping SHC replication wait"
            )
            return

        logger.debug(
            f"[OAuth Endpoint] Waiting {SHC_REPLICATION_WAIT_SECONDS}s for "
            "password.conf replication across SHC nodes"
        )
        time.sleep(SHC_REPLICATION_WAIT_SECONDS)

    def _release_entrant_lock(
        self, account_name: str, session_key: str, adapter: SplunkServiceAdapter
    ) -> None:
        """
        Release distributed entry-point lock.

        This should always be called in a finally block to ensure lock release
        even if an exception occurs.

        Args:
            account_name: Account name to release lock for
            session_key: Splunk session key
            adapter: SplunkServiceAdapter instance for Splunk API calls
        """
        lock_key = f"entrant_lock_{account_name}"
        max_retries = 3

        for attempt in range(max_retries):
            try:
                adapter.kv_store.delete(ENTRANT_LOCK_COLLECTION, lock_key)
                logger.debug(
                    f"[OAuth Endpoint] Released entrant lock for '{account_name}'"
                )
                return
            except KVStoreError as e:
                if '404' in str(e):
                    # Lock already released or expired - this is fine
                    logger.debug(
                        f"[OAuth Endpoint] Entrant lock for '{account_name}' already released"
                    )
                    return
                if attempt < max_retries - 1:
                    delay = 0.5 * (attempt + 1)
                    logger.warning(
                        f"[OAuth Endpoint] Failed to release entrant lock for '{account_name}' "
                        f"(attempt {attempt + 1}/{max_retries}), retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"[OAuth Endpoint] Failed to release entrant lock for '{account_name}' "
                        f"after {max_retries} attempts. Lock will expire in {ENTRANT_LOCK_TIMEOUT_SECONDS}s. "
                        f"Error: {e}"
                    )
            except Exception as e:
                if '404' in str(e):
                    logger.debug(
                        f"[OAuth Endpoint] Entrant lock for '{account_name}' already released"
                    )
                    return
                if attempt < max_retries - 1:
                    delay = 0.5 * (attempt + 1)
                    logger.warning(
                        f"[OAuth Endpoint] Unexpected error releasing entrant lock "
                        f"(attempt {attempt + 1}/{max_retries}), retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"[OAuth Endpoint] Failed to release entrant lock for '{account_name}' "
                        f"after {max_retries} attempts. Lock will expire in {ENTRANT_LOCK_TIMEOUT_SECONDS}s. "
                        f"Error: {e}"
                    )


if __name__ == "__main__":
    admin.init(OAuthTokenHandler, admin.CONTEXT_NONE)
