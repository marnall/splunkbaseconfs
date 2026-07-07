import os
import sys
import json
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import dependency_handler  # noqa: F401  # Do not delete

from libs.base_objects.custom_splunk_endpoint_base import CustomSplunkEndpointBase
from libs.constants import KV_STORE_USER_SETTINGS, USER_SETTINGS_SYSTEM_PROFILE
from libs.kvstore_manager import KVStoreManager


class SourcetypesToggleHandler(
    CustomSplunkEndpointBase, PersistentServerConnectionApplication
):
    """Handler for enabling or disabling specific sourcetypes."""

    def __init__(self, command_line, command_arg, logger=None):
        PersistentServerConnectionApplication.__init__(self)
        CustomSplunkEndpointBase.__init__(self)

    def process_payload(self, payload):
        """Process the payload to enable/disable sourcetypes."""
        sourcetypes_to_enable = self._extract_sourcetypes(payload.get("payload", ""))

        if not sourcetypes_to_enable:
            return self._create_response("No valid sourcetypes found in payload", 400)

        self._save_sourcetypes(sourcetypes_to_enable)

        return self._create_response("Processed sourcetypes successfully", 200)

    def _save_sourcetypes(self, saved_searches_to_enable):
        """Enable or disable sourcetypes based on input."""
        try:
            kv = KVStoreManager(
                KV_STORE_USER_SETTINGS, splunk_service=self.splunk_service
            )
            # For now we'll be updating all existing configurations. At some point we should let the user
            #   save several "profiles"
            updated = False
            for setting in kv.get_all():
                if (
                    setting.get("_key")
                    and setting.get("sourcetypes")
                    and setting.get("profile") != USER_SETTINGS_SYSTEM_PROFILE
                ):
                    kv.update(
                        setting["_key"], {"sourcetypes": saved_searches_to_enable}
                    )
                    updated = True
            if not updated:
                kv.insert(
                    {
                        "sourcetypes": saved_searches_to_enable,
                        "enabled": True,
                        "profile": "user",
                    }
                )

        except Exception as e:
            self.aiq_logger.error(f"Failed to enable/disable sourcetypes: {e}")
            raise RuntimeError(f"Failed to enable/disable sourcetypes: {e}")

    def _extract_sourcetypes(self, payload):
        """Extract the sourcetypes list from the payload."""
        try:
            sourcetypes_str = json.loads(payload).get("sourcetypes", "")
            return sourcetypes_str.split(",")
        except json.JSONDecodeError as e:
            self.aiq_logger.error(f"Failed to parse JSON payload: {e}")
            raise ValueError("Invalid payload format, expected JSON")
