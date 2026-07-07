import import_declare_test  # noqa F401, E402

import os
import sys
import time

from typing import Optional

from splunklib import modularinput as smi
from tenacity import retry, stop_after_attempt, wait_fixed

from thousandeyes_account_manager import ThousandEyesAccountManager
from thousandeyes_utils import parse_boolean
from thousandeyes_client import ThousandEyesClient
from log_helper import setup_logging
from thousandeyes_constant import THOUSANDEYES_TA_NAME # noqa E402


logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0].lower())


class TokenRefresher(smi.Script):
    """
    Splunk modular input for refreshing ThousandEyes OAuth tokens.

    This input runs on a schedule to refresh all stored refresh_tokens
    in the ThousandEyes realm, preventing token expiration.
    """

    def get_scheme(self) -> smi.Scheme:
        """
        Define the modular input scheme.

        Returns:
            smi.Scheme: Configured scheme for the modular input.
        """
        scheme = smi.Scheme("thousandeyes_refresh_tokens")
        scheme.description = "Refreshes stored ThousandEyes refresh_tokens weekly"
        scheme.use_external_validation = False
        scheme.use_single_instance = False  # This parameter allows to run the script multiple times with scheduled interval
        scheme.streaming_mode = smi.Scheme.streaming_mode_xml

        # Add account_refresh_sleep_interval parameter for controlling refresh intervals
        account_refresh_sleep_interval_arg = smi.Argument("account_refresh_sleep_interval")
        account_refresh_sleep_interval_arg.description = "Sleep interval between account refreshes in seconds. Default: 60 (1 min)"
        account_refresh_sleep_interval_arg.data_type = smi.Argument.data_type_number
        account_refresh_sleep_interval_arg.required_on_edit = False
        account_refresh_sleep_interval_arg.required_on_create = False
        account_refresh_sleep_interval_arg.default_value = "60"
        scheme.add_argument(account_refresh_sleep_interval_arg)


        # Add dry_run parameter for testing
        dry_run_arg = smi.Argument("dry_run")
        dry_run_arg.description = "Test mode - log actions without making changes"
        dry_run_arg.data_type = smi.Argument.data_type_boolean
        dry_run_arg.required_on_edit = False
        dry_run_arg.required_on_create = False
        scheme.add_argument(dry_run_arg)

        return scheme

    def validate_input(self, validation_definition: smi.ValidationDefinition) -> None:
        """
        Validate the input configuration.

        Args:
            validation_definition: The validation definition from Splunk.
        """
        # No validation required for this input
        pass

    def stream_events(self, inputs: smi.InputDefinition, ew: Optional[smi.EventWriter] = None) -> None:
        """
        Main token refresh logic.

        Args:
            inputs: Input definitions from Splunk.
            ew: Event writer for logging and creating events.
        """
        for input_name, input_item in inputs.inputs.items():
            # Parse input parameters
            interval = int(input_item.get("interval", 604800))
            account_refresh_sleep_interval = int(input_item.get("account_refresh_sleep_interval", 60))
            dry_run = parse_boolean(input_item.get("dry_run", "false"))

            logger.info(f"Token refresh job started (dry_run={dry_run}, interval={interval})")

            session_key = self._input_definition.metadata["session_key"]

            try:
                result = self._refresh_all_tokens(session_key, account_refresh_sleep_interval, dry_run)
                logger.info(f"Token refresh job completed successfully. Refreshed {result} tokens.")

            except Exception as e:
                logger.error(f"Token refresh failed: {e}", exc_info=True)

    @retry(wait=wait_fixed(600), stop=stop_after_attempt(3), reraise=True)
    def _refresh_all_tokens(
        self,
        session_key: str,
        account_refresh_sleep_interval: int = 60,
        dry_run: bool = False,
    ) -> int:
        """
        Refresh all tokens for the specified realm with retry logic.

        Args:
            session_key: Splunk session key for API access.
            dry_run: Test mode - log actions without making changes.

        Returns:
            int: Number of tokens successfully refreshed.

        Raises:
            Exception: If there's an error connecting to Splunk or refreshing tokens.
        """
        try:
            refreshed_count = 0
            processed_count = 0

            # Initialize ThousandEyes account manager
            te_account_manager = ThousandEyesAccountManager(session_key)
            logger.debug("Initialized ThousandEyes account manager")

            # Filter credentials for ThousandEyes realm
            te_accounts = list(te_account_manager.get_all_accounts().keys())
            logger.debug(f"Account names: {te_accounts}")
            total_amount = len(te_accounts)
            logger.debug(f"Found {total_amount} credentials in the realm '{THOUSANDEYES_TA_NAME}'")

            for username in te_accounts:
                processed_count += 1

                try:
                    logger.debug(
                        f"Refreshing credential {processed_count}/{total_amount} for user: {username}"
                    )

                    if dry_run:
                        logger.debug(f"DRY RUN: Would refresh token for user: {username}")
                        refreshed_count += 1
                        continue

                    # Initialize ThousandEyes client
                    te_client = ThousandEyesClient(
                        session_key=session_key,
                        account_name=username,
                        logger=logger,
                    )
                    logger.debug(f"Initialized ThousandEyes client for user: {username}")

                    # Regenerate access tokens
                    access_token, refresh_token = te_client.regenerate_access_tokens()
                    if not access_token or not refresh_token:
                        logger.error(f"Failed to regenerate access tokens for user: {username}")
                        continue

                    refreshed_count += 1

                    # Update the credentials in Splunk
                    te_account_manager.update_access_token(access_token, refresh_token, username)

                    # Sleep between account refreshes if configured
                    if refreshed_count < total_amount:
                        logger.debug(
                            f"Waiting for {account_refresh_sleep_interval} seconds before next account refresh"
                        )
                        time.sleep(account_refresh_sleep_interval)

                except Exception as e:
                    logger.error(f"Error processing user {username}.")

            logger.info(f"Token refresh completed. Processed {processed_count} credentials, refreshed {refreshed_count} tokens.")
            return refreshed_count

        except Exception as e:
            logger.error(f"Error in _refresh_all_tokens: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    sys.exit(TokenRefresher().run(sys.argv))
