import ta_analyst1_declare  # noqa:F401
import traceback
import os
import sys

# Add path for custom credentials class
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ta_analyst1'))

from analyst1_helpers.conf_helper import get_conf_file
from analyst1_helpers.validators import IndicatorValidator
from analyst1_logging import get_logger
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.handler import RestHandler
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunk_client.splunk_ta_conf.analyst1_rest_credentials import Analyst1RestCredentials
import splunk.rest as rest


util.remove_http_proxy_env_vars()


class Analyst1RestHandler(RestHandler):
    """
    Custom REST handler that uses Analyst1RestCredentials to prevent OAuth token corruption.

    This handler overrides the default RestHandler to inject our custom credentials class
    that protects OAuth fields (access_token, token_expiry, client_secret) from being
    corrupted when modular input settings are updated.

    See analyst1_rest_credentials.py for detailed explanation of the OAuth corruption issue.
    """

    def __init__(self, splunkd_uri, session_key, endpoint, *args, **kwargs):
        # Call parent constructor
        super().__init__(splunkd_uri, session_key, endpoint, *args, **kwargs)

        # Replace the default RestCredentials with our custom implementation
        # This prevents OAuth token corruption during input configuration updates
        self.rest_credentials = Analyst1RestCredentials(
            splunkd_uri,
            session_key,
            endpoint,
        )


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server with OAuth-safe credentials handling.

    This handler extends ConfigMigrationHandler and overrides handler initialization
    to use Analyst1RestHandler, which prevents OAuth token corruption when modular
    input settings are updated.

    :param ConfigMigrationHandler: inheriting ConfigMigrationHandler
    """

    def __init__(self, *args, **kwargs):
        """
        Override initialization to inject custom REST handler with OAuth protection.
        """
        # Call parent __init__ first (this initializes self.handler with default RestHandler)
        super().__init__(*args, **kwargs)

        # Replace the handler with our custom implementation that protects OAuth fields
        from solnlib.splunkenv import get_splunkd_uri
        import os

        def get_splunkd_endpoint():
            if os.environ.get("SPLUNKD_URI"):
                return os.environ["SPLUNKD_URI"]
            else:
                splunkd_uri = get_splunkd_uri()
                os.environ["SPLUNKD_URI"] = splunkd_uri
                return splunkd_uri

        self.handler = Analyst1RestHandler(
            get_splunkd_endpoint(),
            self.getSessionKey(),
            self.endpoint,
        )

    def _get_checkpoint_base_url(self):
        """Get the base URL for checkpoint operations."""
        app_name = __file__.split(os.sep)[-3]
        return "/servicesNS/nobody/{}/storage/collections/data/TA_Analyst1_checkpointer/".format(
            app_name
        )

    def delete_checkpoint(self, checkpoint_key):
        """Delete a single checkpoint entry by key.
        :param checkpoint_key: The key of the checkpoint to delete
        """
        session_key = self.getSessionKey()
        url = self._get_checkpoint_base_url() + checkpoint_key
        try:
            _, _ = rest.simpleRequest(
                url,
                sessionKey=session_key,
                method="DELETE",
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )
        except Exception:
            raise

    def _cleanup_input_sensor_states(self, input_name, handler_logger):
        """
        Remove entries for a deleted input from the input_sensor_states checkpoint.

        The input_sensor_states checkpoint stores version info with keys like:
        {input_name}_{sensor_id}_{indicator_type}_version

        This method removes all entries that start with the deleted input's name.
        """
        import json
        session_key = self.getSessionKey()
        url = self._get_checkpoint_base_url() + "input_sensor_states"

        try:
            # Read current input_sensor_states
            _, content = rest.simpleRequest(
                url,
                sessionKey=session_key,
                method="GET",
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )

            checkpoint_data = json.loads(content)
            state_str = checkpoint_data.get("state", "{}")
            current_states = json.loads(state_str) if isinstance(state_str, str) else state_str

            if not current_states:
                return

            # Find and remove entries for this input
            # Keys are formatted as: {input_name}_{sensor_id}_{indicator_type}_version
            prefix = f"{input_name}_"
            keys_to_remove = [k for k in current_states.keys() if k.startswith(prefix)]

            if not keys_to_remove:
                handler_logger.debug(
                    f"input_name={input_name} | message=no_sensor_states_to_cleanup | "
                    f"No input_sensor_states entries found for input"
                )
                return

            for key in keys_to_remove:
                del current_states[key]

            # Save updated states
            updated_data = {"_key": "input_sensor_states", "state": json.dumps(current_states)}
            _, _ = rest.simpleRequest(
                url,
                sessionKey=session_key,
                method="POST",
                jsonargs=json.dumps(updated_data),
                raiseAllErrors=True,
            )

            handler_logger.info(
                f"input_name={input_name} | message=sensor_states_cleaned | "
                f"Removed {len(keys_to_remove)} input_sensor_states entries: {keys_to_remove}"
            )

        except Exception as e:
            # Log but don't fail - this is cleanup, not critical
            handler_logger.warning(
                f"input_name={input_name} | message=sensor_states_cleanup_warning | "
                f"Could not clean input_sensor_states: {e}"
            )

    def handleRemove(self, conf_info):
        """
        Handles the delete operation.
        Cleans up checkpoint data for the deleted input before removing it.

        :param confInfo: Default parameter generated by AOB which is used to pass the response
        """
        input_name = self.callerArgs.id
        input_stanza_name = "analyst1_indicator://" + input_name
        session_key = self.getSessionKey()
        handler_logger = get_logger("ta_analyst1_rest_handler")

        try:
            input_stanza = get_conf_file(
                file="inputs", stanza=input_stanza_name, session_key=session_key
            )
            sensor_id = input_stanza.get("sensor_id")
            account_name = input_stanza.get("global_account")

            # Clean up legacy checkpoint keys (for backwards compatibility)
            legacy_keys = [
                "{}_{}_{}_last_version".format(account_name, input_name, sensor_id),
                "{}_{}_{}_last_refresh".format(account_name, input_name, sensor_id),
            ]
            for key in legacy_keys:
                try:
                    self.delete_checkpoint(key)
                except Exception:
                    pass  # Legacy keys may not exist

            # Clean up input_sensor_states entries for this input
            self._cleanup_input_sensor_states(input_name, handler_logger)

            handler_logger.info(
                f"input_name={input_name} | message=checkpoint_cleanup_complete | "
                f"Checkpoint cleanup completed for input: {input_name}"
            )

        except Exception:
            handler_logger.error(
                "input_name={} | message=checkpoint_deletion_error | Error occurred while deleting checkpoint."
                " Error: {}".format(input_name, traceback.format_exc())
            )
        finally:
            super(CustomConfigMigrationHandler, self).handleRemove(conf_info)


class IntervalConvertor:
    def encode(self, interval, _):
        """
        Minutes -> Seconds
        """
        return int(interval) * 60

    def decode(self, interval, _):
        """
        Seconds -> Minutes
        """
        return int(int(interval) / 60)


fields = [
    field.RestField(
        "index",
        required=False,
        encrypted=False,
        default="default",
        validator=validator.String(
            min_len=1,
            max_len=80,
        ),
    ),
    field.RestField(
        "global_account",
        required=True,
        encrypted=False,
        default=None,
        validator=IndicatorValidator(),
    ),
    field.RestField(
        "indicator_types", required=True, encrypted=False, default="All", validator=None
    ),
    field.RestField(
        "sensor_id", required=True, encrypted=False, default=None, validator=None
    ),
    # field.RestField(
    #     "refresh_factor", required=True, encrypted=False, default="1440", validator=None
    # ), TODO evaluate removal
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "analyst1_indicator",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )
