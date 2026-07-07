import os
import sys
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import dependency_handler  # noqa: F401  # Do not delete

from libs.base_objects.custom_splunk_endpoint_base import CustomSplunkEndpointBase
from libs.kvstore_manager import KVStoreManager
from libs.migration_manager import MigrationManager


class FlexDataMigrationsHandler(
    CustomSplunkEndpointBase, PersistentServerConnectionApplication
):
    def __init__(self, command_line, command_arg, logger=None):
        PersistentServerConnectionApplication.__init__(self)
        CustomSplunkEndpointBase.__init__(self)
        self.kv_store_manager = None

    def process_payload(self, payload):
        """Process the payload for different actions."""
        try:
            self.aiq_logger.info(
                "handler=FlexDataMigrationsHandler action=process_payload"
            )
            self.kv_store_manager = KVStoreManager(
                collection_name="migration_status",
                splunk_service=self.splunk_service,
                logger=self.aiq_logger,
            )
            self.migration_manager = MigrationManager(
                self.kv_store_manager,
                splunk_service=self.splunk_service,
                logger=self.aiq_logger,
            )
            method = self._get_method(payload)
            self.aiq_logger.info(f"Processing payload with method: {method}")
            if method == "GET":
                return self._handle_get_migrations()
            elif method == "POST":
                return self._handle_post_migrations(payload)
            else:
                return self._create_response(f"Unsupported method: {method}", 400)
        except Exception as e:
            self.aiq_logger.error(f"Failed to process payload: {e}")
            return self._create_response(f"Failed to process payload: {e}", 500)

    def _get_method(self, payload):
        """Determine the method (GET or POST) based on the payload or HTTP request."""
        if "method" in payload:
            return payload["method"].upper()
        return "GET"  # Default to GET if no method is specified

    def _handle_get_migrations(self):
        """Handle the GET request: Return all migration statuses."""
        try:
            migrations_status = self.kv_store_manager.get_all()
            self.aiq_logger.info(
                "Retrieved migration statuses", {"status": migrations_status}
            )

            return self._create_response(
                "Migration statuses retrieved successfully",
                200,
                results=self.format_migrations_status_response(migrations_status),
            )
        except Exception as e:
            self.aiq_logger.error(f"Error fetching migration statuses: {str(e)}")
            return self._create_response(
                f"Error fetching migration statuses: {str(e)}", 500
            )

    def _handle_post_migrations(self, payload):
        """Handle the POST request: Execute migrations (either all or one)."""
        migration_id = self._get_migration_id(payload)
        if migration_id:
            return self._execute_single_migration(migration_id)
        else:
            return self._execute_all_migrations()

    def _get_migration_id(self, payload):
        """Retrieve the migration id from the payload."""
        self.aiq_logger.info(
            f"_get_migration_id Retrieving migration_id from the payload. {payload}"
        )
        query_values = payload.get("query", [])
        self.aiq_logger.info(f"_get_migration_id Query values: {query_values}")
        for query in query_values:
            if query[0] == "migration_id":
                self.aiq_logger.info(
                    f"_get_migration_id Found migration_id: {query[1]}"
                )
                return query[1]
        self.aiq_logger.info(
            f"_get_migration_id No migration_id found in the payload {query_values}"
        )
        return None

    def _execute_all_migrations(self):
        """Execute all migrations."""
        try:
            self.aiq_logger.info("Starting to execute all migrations.")
            migrations_run = self.migration_manager.run_all_migrations()
            self.aiq_logger.info(
                "Executed all migrations", {"migration_run": migrations_run}
            )
            return self._create_response("All migrations executed successfully", 200)
        except Exception as e:
            self.aiq_logger.error(f"Error executing all migrations: {str(e)}")
            return self._create_response(
                f"Error executing all migrations: {str(e)}", 500
            )

    def _execute_single_migration(self, migration_id):
        """Execute a single migration based on migration_id."""
        try:
            self.aiq_logger.info(f"Starting migration process {migration_id}.")
            self.migration_manager.run_migration_by_id(migration_id)
            self.aiq_logger.info(f"Executed migration {migration_id}")
            return self._create_response(
                f"Migration {migration_id} executed successfully", 200
            )
        except ValueError as e:
            self.aiq_logger.error(f"Migration {migration_id} not found: {str(e)}")
            return self._create_response(f"Migration {migration_id} not found", 404)
        except Exception as e:
            self.aiq_logger.error(f"Error executing migration {migration_id}: {str(e)}")
            return self._create_response(
                f"Error executing migration {migration_id}: {str(e)}", 500
            )

    def format_migrations_status_response(self, migrations_status):
        """Format the migration status response."""
        return {
            "migrations": [
                {
                    "Migration Name": migration.get("_key", "N/A"),
                    "Execution Date": migration.get("executed_at", "N/A"),
                    "Prerequisites": migration.get("prerequisite_status", "N/A"),
                    "Status": migration.get("status", "N/A"),
                    "Outcome": migration.get("stats", "N/A"),
                    "Retry Count": migration.get("retry_count", 0),
                    "Error Message": migration.get("error", ""),
                }
                for migration in migrations_status
            ]
        }
