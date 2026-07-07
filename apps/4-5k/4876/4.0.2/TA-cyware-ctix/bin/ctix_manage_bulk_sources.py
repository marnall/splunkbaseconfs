"""Manage CTIX bulk indicator sources."""

import ta_cyware_ctix_declare  # noqa: F401

import sys
import json
import time
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from ta_cyware_ctix.logging_helper import get_logger
from ta_cyware_ctix.kvstore_helper import CollectionManager

logger = get_logger("ctix_manage_bulk_sources")


@Configuration()
class CTIXManageBulkSourcesCommand(GeneratingCommand):
    """
    Command to manage CTIX bulk indicator sources in KV Store.

    Usage:
        | ctixmanagebulksources action="add" source_name="..." source_type="index" ...
        | ctixmanagebulksources action="delete" key="..."
    """

    action = Option(require=True)
    key = Option(require=False, default=None)
    source_name = Option(require=False, default=None)
    source_type = Option(require=False, default=None)
    index_name = Option(require=False, default=None)
    sourcetype = Option(require=False, default=None)
    cim_datamodel_name = Option(require=False, default=None)
    cim_field_name = Option(require=False, default=None)
    datamodel_name = Option(require=False, default=None)
    lookup_name = Option(require=False, default=None)
    field_name = Option(require=False, default=None)
    source_name_metadata = Option(require=False, default="Splunk")
    tlp = Option(require=False, default="AMBER")
    confidence = Option(require=False, default="100")
    tags = Option(require=False, default=None)
    description = Option(require=False, default=None)
    collection_name = Option(require=False, default=None)
    splunk_account = Option(require=False, default=None)

    def _validate_source_type_index(self):
        """Validate index source type."""
        if not self.index_name:
            return "index_name is required for source_type=index"
        if not self.field_name:
            return "field_name is required for source_type=index"
        return None

    def _validate_source_type_cim(self):
        """Validate CIM source type."""
        if not self.cim_datamodel_name:
            return "cim_datamodel_name is required for source_type=cim"
        if not self.cim_field_name:
            return "cim_field_name is required for source_type=cim"
        return None

    def _validate_source_type_custom_datamodel(self):
        """Validate custom datamodel source type."""
        if not self.datamodel_name:
            return "datamodel_name is required for source_type=custom_datamodel"
        if not self.field_name:
            return "field_name is required for source_type=custom_datamodel"
        return None

    def _validate_source_type_lookup(self):
        """Validate lookup source type."""
        if not self.lookup_name:
            return "lookup_name is required for source_type=lookup"
        if not self.field_name:
            return "field_name is required for source_type=lookup"
        return None

    def _validate_add_action(self):
        """Validate required fields for add action."""
        if not self.source_name or not self.source_type or not self.splunk_account:
            return "Required fields: source_name, source_type, splunk_account"

        validators = {
            "index": self._validate_source_type_index,
            "cim": self._validate_source_type_cim,
            "custom_datamodel": self._validate_source_type_custom_datamodel,
            "lookup": self._validate_source_type_lookup
        }

        validator = validators.get(self.source_type)
        if validator:
            return validator()

        return None

    def _handle_add_action(self, collection):
        """Handle add action."""
        validation_error = self._validate_add_action()
        if validation_error:
            return {"status": "error", "message": validation_error}

        current_time = int(time.time())
        record = {
            "source_name": self.source_name,
            "source_type": self.source_type,
            "index_name": self.index_name or None,
            "sourcetype": self.sourcetype or None,
            "cim_datamodel_name": self.cim_datamodel_name or None,
            "cim_field_name": self.cim_field_name or None,
            "datamodel_name": self.datamodel_name or None,
            "lookup_name": self.lookup_name or None,
            "field_name": self.field_name or None,
            "source_name_metadata": self.source_name_metadata,
            "tlp": self.tlp,
            "confidence": int(self.confidence),
            "tags": self.tags or None,
            "description": self.description or None,
            "collection_name": self.collection_name or None,
            "splunk_account": self.splunk_account,
            "status": "active",
            "checkpoint_time": 0,
            "checkpoint_row": 0,
            "last_run": 0,
            "last_status": "never_run",
            "created_time": current_time,
            "updated_time": current_time
        }

        result = collection.data.insert(json.dumps(record))
        record["_key"] = result["_key"]
        record["status"] = "success"
        record["message"] = f"Source added successfully with key: {result['_key']}"
        return record

    def _build_update_data(self):
        """Build update data dictionary."""
        update_data = {}
        fields = [
            ('source_name', self.source_name),
            ('source_type', self.source_type),
            ('index_name', self.index_name),
            ('sourcetype', self.sourcetype),
            ('cim_datamodel_name', self.cim_datamodel_name),
            ('cim_field_name', self.cim_field_name),
            ('datamodel_name', self.datamodel_name),
            ('lookup_name', self.lookup_name),
            ('field_name', self.field_name),
            ('source_name_metadata', self.source_name_metadata),
            ('tlp', self.tlp),
            ('tags', self.tags),
            ('description', self.description),
            ('collection_name', self.collection_name),
            ('splunk_account', self.splunk_account)
        ]

        for field_name, field_value in fields:
            if field_value:
                if field_name == 'confidence' and self.confidence:
                    update_data['confidence'] = int(self.confidence)
                else:
                    update_data[field_name] = field_value

        if self.confidence:
            update_data['confidence'] = int(self.confidence)

        update_data["updated_time"] = int(time.time())
        return update_data

    def _handle_update_action(self, collection):
        """Handle update action."""
        if not self.key:
            return {"status": "error", "message": "key is required for update action"}

        # Check if record exists
        record = collection.query_by_id(self.key)
        if not record:
            return {"status": "error", "message": f"Record not found with key: {self.key}"}

        update_data = self._prepare_update_data()
        update_data["_key"] = self.key

        try:
            collection.upsert([update_data])
            return {
                "status": "success",
                "message": "Source updated successfully",
                "_key": self.key
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to update source: {str(e)}"
            }

    def _handle_delete_action(self, collection):
        """Handle delete action."""
        if not self.key:
            return {"status": "error", "message": "key is required for delete action"}

        try:
            # Check if record exists
            record = collection.query_by_id(self.key)
            if not record:
                return {"status": "error", "message": f"Record not found with key: {self.key}"}

            # Delete using batch delete with _key query
            collection.delete_batch({"_key": self.key})
            return {
                "status": "success",
                "message": "Source deleted successfully",
                "_key": self.key
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete source: {str(e)}"
            }

    def _handle_enable_disable_action(self, collection):
        """Handle enable/disable action."""
        if not self.key:
            return {
                "status": "error",
                "message": f"key is required for {self.action} action"
            }

        new_status = "active" if self.action == "enable" else "disabled"
        update_data = {
            "status": new_status,
            "updated_time": int(time.time())
        }

        try:
            collection.upsert([{"_key": self.key, **update_data}])
            return {
                "status": "success",
                "message": f"Source {self.action}d successfully",
                "_key": self.key
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to {self.action} source: {str(e)}"
            }

    def generate(self):
        """Generate command results."""
        try:
            # Use CollectionManager for better connection handling (RedHat OS fix)
            collection = CollectionManager(
                collection_name="ctix_bulk_indicator_sources",
                session_key=self._metadata.searchinfo.session_key
            )

            if self.action == "list":
                records = collection.get()
                for record in records:
                    yield record
            elif self.action == "add":
                yield self._handle_add_action(collection)
            elif self.action == "update":
                yield self._handle_update_action(collection)
            elif self.action == "delete":
                yield self._handle_delete_action(collection)
            elif self.action in ["enable", "disable"]:
                yield self._handle_enable_disable_action(collection)
            else:
                yield {
                    "status": "error",
                    "message": f"Unknown action: {self.action}. "
                    "Valid actions: list, add, update, delete, enable, disable"
                }

        except Exception as e:
            yield {
                "status": "error",
                "message": f"Error managing bulk sources: {str(e)}"
            }


dispatch(CTIXManageBulkSourcesCommand, sys.argv, sys.stdin, sys.stdout, __name__)
