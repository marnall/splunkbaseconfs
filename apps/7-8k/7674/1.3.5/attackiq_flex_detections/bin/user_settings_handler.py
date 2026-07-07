import os
import sys
import json
from typing import Dict
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import dependency_handler  # noqa: F401  # Do not delete

from libs.base_objects.custom_splunk_endpoint_base import CustomSplunkEndpointBase
from libs.base_objects.table_structures import UserSettingsModel
from libs.constants import KV_STORE_USER_SETTINGS
from libs.kvstore_manager import KVStoreManager


class UserSettingsHandler(
    CustomSplunkEndpointBase, PersistentServerConnectionApplication
):
    """Handler for managing user settings."""

    def __init__(self, command_line, command_arg, logger=None):
        PersistentServerConnectionApplication.__init__(self)
        CustomSplunkEndpointBase.__init__(self)

    def process_payload(self, payload: Dict) -> Dict:
        """Process the payload to handle user settings."""
        try:
            data = self._parse_payload(payload.get("payload", ""))
            user_settings = UserSettingsModel(data)
            user_settings.validate()

            self._save_user_settings(user_settings.to_dict())

            return self._create_response("Processed user settings successfully", 200)
        except ValueError as e:
            self.aiq_logger.error(f"ValueError processing user settings payload: {e}")
            return self._create_response(str(e), 400)
        except Exception as e:
            self.aiq_logger.error(f"Error processing user settings payload: {e}")
            return self._create_response(f"Unexpected error: {e}", 500)

    def _parse_payload(self, payload: str) -> Dict:
        """Parse and deserialize the payload."""
        if not payload:
            raise ValueError("Payload is empty or missing.")

        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in payload.")

    def _save_user_settings(self, settings: Dict) -> None:
        """Save the user settings to the KV store."""
        kv = KVStoreManager(KV_STORE_USER_SETTINGS, splunk_service=self.splunk_service)

        try:
            existing_record = self._find_existing_record(kv, settings["profile"])

            if existing_record:
                self._update_existing_record(kv, existing_record, settings)
            else:
                self._insert_new_record(kv, settings)

        except Exception as e:
            self.aiq_logger.error(f"Failed to save user settings: {e}")
            raise RuntimeError(f"Failed to save user settings: {e}")

    def _find_existing_record(self, kv: KVStoreManager, profile: str) -> Dict:
        """Find an existing record in the KV store by profile."""
        for record in kv.get_all():
            if record.get("profile") == profile:
                return record
        return None

    def _update_existing_record(
        self, kv: KVStoreManager, record: Dict, new_settings: Dict
    ) -> None:
        """Update an existing record with new settings."""
        merged_sourcetypes = list(
            set(record.get("sourcetypes", []) + new_settings["sourcetypes"])
        )
        merged_indexes = list(set(record.get("indexes", []) + new_settings["indexes"]))

        updated_settings = {
            **record,
            **new_settings,
            "sourcetypes": merged_sourcetypes,
            "indexes": merged_indexes,
        }

        kv.update(record["_key"], updated_settings)

    def _insert_new_record(self, kv: KVStoreManager, settings: Dict) -> None:
        """Insert a new record into the KV store."""
        kv.insert(settings)
