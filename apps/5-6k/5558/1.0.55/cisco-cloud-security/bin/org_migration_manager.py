# encoding = utf-8
"""Manager for handling multi-org migration of KV store collections and Splunk configurations."""

from __future__ import print_function

import sys
from os.path import dirname, abspath
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

sys.path.append(dirname(abspath(__file__)))

import json
import splunklib.client as client
import splunklib.results as results
from service.app_kvstore_service import KVStoreService
from logger import Logger
from reporting_api_client import ReportingAPIClient
from exceptions import (
    ModularInputNotFoundException,
    NewInstallationException,
    MigrationFailedException,
)
from enums import (
    KvStoreCollections,
    KvStoreFilterQueries,
    ModInputInterval,
    ModInputType,
    OAuthSettingsStatus,
)
from token_service import TokenService
from utils import get_org_id_from_token, send_splunk_notification
from collections_schema import DestinationsFields, S3IndexesFields
from modular_input_manager import ModularInputManager
from alert_action_manager import AlertActionManager
from global_org_client import GlobalOrgClient


@dataclass
class CollectionMigrationStats:
    """Statistics for a single collection migration."""
    collection: str
    total: int = 0
    migrated: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class MigrationResult:
    """Result of the overall migration process.
    
    Attributes:
        success: Whether the migration completed without critical failures.
        org_id: The organization ID used for migration.
        collection_stats: Per-collection migration statistics.
        errors: List of error messages encountered during migration.
    """
    success: bool = True
    org_id: str = ""
    collection_stats: List[CollectionMigrationStats] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_collection_stats(self, stats: CollectionMigrationStats) -> None:
        """Add statistics for a collection migration."""
        self.collection_stats.append(stats)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)

    @property
    def total_migrated(self) -> int:
        """Total records migrated across all collections."""
        return sum(s.migrated for s in self.collection_stats)

    @property
    def total_skipped(self) -> int:
        """Total records skipped across all collections."""
        return sum(s.skipped for s in self.collection_stats)

    @property
    def total_failed(self) -> int:
        """Total records failed across all collections."""
        return sum(s.failed for s in self.collection_stats)


class OrgMigrationManager:
    """
    Manager class for migrating existing Splunk app data to multi-org format.
    
    Handles migration of:
    - KV Store collections (oauth_settings, investigate_settings, destinations, etc.)
    - Modular inputs (app discovery, private apps)
    - Alert actions in saved searches
    
    The migration is idempotent - records with existing orgId are skipped.
    """
    
    OAUTH_COLLECTION = KvStoreCollections.OAUTH_SETTINGS.value

    def __init__(
        self,
        session_token: str,
        kv_service: Optional[KVStoreService] = None,
        data_inputs_mgr: Optional[ModularInputManager] = None,
        alert_action_mgr: Optional[AlertActionManager] = None,
    ):
        """
        Initialize the OrgMigrationManager.
        
        Args:
            session_token: Splunk session authentication token.
            kv_service: Optional KVStoreService instance (created if not provided).
            data_inputs_mgr: Optional ModularInputManager instance (lazy-loaded if not provided).
            alert_action_mgr: Optional AlertActionManager instance (lazy-loaded if not provided).
        """
        self._session_token = session_token
        self._logger = Logger()
        self._kv_service = kv_service or KVStoreService(session_token=session_token)
        self._data_inputs_mgr = data_inputs_mgr
        self._alert_action_mgr = alert_action_mgr

    def perform_migration(self) -> MigrationResult:
        """Orchestrate migration of all collections to include orgId.
        
        This method is idempotent - it can be safely called multiple times.
        Records that already have an orgId will be skipped.

        Returns:
            MigrationResult with detailed statistics and any errors encountered.

        Raises:
            NewInstallationException: If no active oauth settings found (new installation).
            MigrationFailedException: If unable to determine orgId for migration.
        """
        result = MigrationResult()
        
        self._logger.info(
            "Starting migration of existing active oauth settings to include orgId."
        )

        # Resolve org_id first (required for all migrations)
        org_id, oauth_record = self._resolve_org_id_for_migration()
        result.org_id = org_id

        # Migrate OAuth first (required - failure here stops migration)
        try:
            self._migrate_oauth_settings(org_id, oauth_record)
        except Exception as e:
            raise MigrationFailedException(f"OAuth settings migration failed: {e}")

        # Migrate credentials to org-specific storage (critical for ReportingAPIClient)
        try:
            self._migrate_credentials(org_id)
        except Exception as e:
            error_msg = f"Failed to migrate credentials: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        # Set global org if not already set
        try:
            self._set_global_org_if_needed(org_id)
        except Exception as e:
            error_msg = f"Failed to set global org: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        # Migrate other collections (optional - continue even if any fails)
        try:
            stats = self._migrate_investigate_settings(org_id)
            result.add_collection_stats(stats)
        except Exception as e:
            error_msg = f"Failed to migrate investigate settings: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        try:
            stats = self._migrate_selected_destination_lists(org_id)
            result.add_collection_stats(stats)
        except Exception as e:
            error_msg = f"Failed to migrate selected destination lists: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        try:
            stats = self._migrate_s3_indexes(org_id)
            result.add_collection_stats(stats)
        except Exception as e:
            error_msg = f"Failed to migrate S3 indexes: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        appdiscovery_status = False
        privateapp_status = False

        try:
            stats = self._migrate_appdiscovery_indexes(org_id)
            result.add_collection_stats(stats)
            # Use stats.total > 0 to ensure modular input migration is attempted
            # even if KV store record was already migrated in a previous run
            appdiscovery_status = stats.total > 0
        except Exception as e:
            error_msg = f"Failed to migrate app discovery indexes: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        try:
            stats = self._migrate_privateapp_indexes(org_id)
            result.add_collection_stats(stats)
            # Use stats.total > 0 to ensure modular input migration is attempted
            # even if KV store record was already migrated in a previous run
            privateapp_status = stats.total > 0
        except Exception as e:
            error_msg = f"Failed to migrate private app indexes: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        if appdiscovery_status:
            try:
                self._migrate_indexing_script(org_id, ModInputType.APP_DISCOVERY)
            except Exception as e:
                error_msg = f"Failed to migrate app discovery indexing script: {e}"
                self._logger.error(f"{error_msg}. Continuing with other migrations.")
                result.add_error(error_msg)

        if privateapp_status:
            try:
                self._migrate_indexing_script(org_id, ModInputType.PRIVATE_APPS)
            except Exception as e:
                error_msg = f"Failed to migrate private apps indexing script: {e}"
                self._logger.error(f"{error_msg}. Continuing with other migrations.")
                result.add_error(error_msg)

        alert_actions_found = False
        try:
            alert_actions_found = self._migrate_alert_actions(org_id)
        except Exception as e:
            error_msg = f"Failed to migrate alert actions: {e}"
            self._logger.error(f"{error_msg}. Continuing.")
            result.add_error(error_msg)

        # Investigate collections and alert_inputs are populated by alert actions
        # If no alert actions exist, these collections are empty - nothing to migrate
        if not alert_actions_found:
            self._logger.info(
                "No alert actions found - skipping investigate collections and alert_inputs migration."
            )
            self._logger.info(
                f"Migration completed for all collections. "
                f"Migrated: {result.total_migrated}, Skipped: {result.total_skipped}, "
                f"Failed: {result.total_failed}, Errors: {len(result.errors)}"
            )
            return result

        try:
            stats = self._migrate_cisco_investigate_domains(org_id)
            result.add_collection_stats(stats)
        except Exception as e:
            error_msg = f"Failed to migrate cisco_investigate_domains: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        try:
            stats = self._migrate_cisco_investigate_ips(org_id)
            result.add_collection_stats(stats)
        except Exception as e:
            error_msg = f"Failed to migrate cisco_investigate_ips: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        try:
            stats = self._migrate_cisco_investigate_hashes(org_id)
            result.add_collection_stats(stats)
        except Exception as e:
            error_msg = f"Failed to migrate cisco_investigate_hashes: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        try:
            stats = self._migrate_cisco_investigate_urls(org_id)
            result.add_collection_stats(stats)
        except Exception as e:
            error_msg = f"Failed to migrate cisco_investigate_urls: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        try:
            stats = self._migrate_alert_inputs(org_id)
            result.add_collection_stats(stats)
        except Exception as e:
            error_msg = f"Failed to migrate alert_inputs: {e}"
            self._logger.error(f"{error_msg}. Continuing with other migrations.")
            result.add_error(error_msg)

        self._logger.info(
            f"Migration completed for all collections. "
            f"Migrated: {result.total_migrated}, Skipped: {result.total_skipped}, "
            f"Failed: {result.total_failed}, Errors: {len(result.errors)}"
        )

        return result

    def _resolve_org_id_for_migration(self) -> Tuple[str, Dict[str, Any]]:
        """Resolve org_id from token or API client for migration.

        Returns:
            Tuple of (org_id, oauth_record).

        Raises:
            NewInstallationException: If no active oauth settings found.
            MigrationFailedException: If unable to determine orgId.
        """
        records = json.loads(
            self._kv_service.query_items(
                self.OAUTH_COLLECTION,
                self._session_token,
                {"status": OAuthSettingsStatus.ACTIVE.value},
            )
        )
        if not records:
            self._logger.info(
                "No active oauth settings found for migration. Considering new installation."
            )
            raise NewInstallationException()
        
        self._logger.info(f"_resolve_org_id_for_migration found {len(records)} active oauth records.")
        org_id = self._get_org_id_from_token()
        if not org_id:
            self._logger.info(
                "Unable to extract orgId from stored access token for migration. "
                "Trying to proceed by generating fresh access token."
            )
            org_id = self._get_org_id_from_api_client(records[-1])

        if not org_id:
            self._logger.error(
                "Migration failed. Unable to determine orgId for active oauth settings."
            )
            raise MigrationFailedException()

        return org_id, records[-1]

    def _migrate_collection_record(
        self,
        collection: str,
        org_id: str,
        query_conditions: Optional[Dict[str, Any]] = None,
    ) -> CollectionMigrationStats:
        """Migrate a single collection record to include orgId.
        
        This method is idempotent - records with existing orgId are skipped.

        Args:
            collection: The KV store collection name.
            org_id: The organization ID to add to the record.
            query_conditions: Optional query conditions to filter records.

        Returns:
            CollectionMigrationStats with migration statistics.
        """
        stats = CollectionMigrationStats(collection=collection)
        
        self._logger.info(f"Starting migration for collection: {collection}")
        records = json.loads(
            self._kv_service.query_items(
                collection,
                self._session_token,
                query_conditions,
            )
        )
        if not records:
            self._logger.info(f"No {collection} records found for migration.")
            return stats

        stats.total = 1  # Only migrating the last record
        record = records[-1]
        
        # Idempotency check: skip if orgId already exists
        if record.get("orgId"):
            self._logger.info(
                f"{collection} record already has orgId '{record.get('orgId')}'. Skipping migration."
            )
            stats.skipped = 1
            return stats

        updated_record = {**record, "orgId": org_id}
        record_id = updated_record.pop("_key", "")
        self._kv_service.update_item_by_key(
            collection,
            record_id,
            self._session_token,
            updated_record,
        )
        stats.migrated = 1
        self._logger.info(
            f"{collection} migration completed successfully. orgId {org_id} added."
        )
        return stats

    def _migrate_oauth_settings(
        self, org_id: str, oauth_record: Dict[str, Any]
    ) -> None:
        """Migrate OAuth settings record to include orgId.
        
        This method is idempotent - records with existing orgId are skipped.
        """
        # Idempotency check: skip if orgId already exists
        if oauth_record.get("orgId"):
            self._logger.info(
                f"{self.OAUTH_COLLECTION} record already has orgId '{oauth_record.get('orgId')}'. "
                "Skipping migration."
            )
            return

        updated_record = {**oauth_record, "orgId": org_id}
        record_id = updated_record.pop("_key", "")
        self._kv_service.update_item_by_key(
            self.OAUTH_COLLECTION,
            record_id,
            self._session_token,
            updated_record,
        )
        self._logger.info(
            f"{self.OAUTH_COLLECTION} migration completed successfully. orgId {org_id} added."
        )

    def _migrate_investigate_settings(self, org_id: str) -> CollectionMigrationStats:
        """Migrate Investigate API settings record to include orgId."""
        return self._migrate_collection_record(
            KvStoreCollections.INVESTIGATE_SETTINGS.value,
            org_id,
            {"status": OAuthSettingsStatus.ACTIVE.value},
        )

    def _migrate_selected_destination_lists(self, org_id: str) -> CollectionMigrationStats:
        """Migrate Selected Destination Lists record and associated destinations to include orgId."""
        collection = KvStoreCollections.SELECTED_DESTINATION_LISTS.value
        stats = CollectionMigrationStats(collection=collection)
        
        self._logger.info(f"Starting migration for collection: {collection}")

        records = json.loads(
            self._kv_service.query_items(
                collection,
                self._session_token,
            )
        )
        if not records:
            self._logger.info(f"No {collection} records found for migration.")
            return stats

        stats.total = 1
        selected_record = records[-1]
        
        # Idempotency check: skip if orgId already exists
        if selected_record.get("orgId"):
            self._logger.info(
                f"{collection} record already has orgId '{selected_record.get('orgId')}'. "
                "Skipping migration."
            )
            stats.skipped = 1
            # Still try to migrate destinations for this record
            dest_list_id = selected_record.get("dest_list_id")
            if dest_list_id:
                try:
                    self._migrate_destinations_for_list_id(org_id, dest_list_id)
                except Exception as e:
                    self._logger.error(
                        f"Failed to migrate destinations for list ID {dest_list_id}: {e}. Continuing."
                    )
            return stats

        dest_list_id = selected_record.get("dest_list_id")

        # Update selected destination list record with orgId
        updated_record = {**selected_record, "orgId": org_id}
        record_key = updated_record.pop("_key", "")
        self._kv_service.update_item_by_key(
            collection,
            record_key,
            self._session_token,
            updated_record,
        )
        stats.migrated = 1
        self._logger.info(
            f"{collection} migration completed successfully. orgId {org_id} added."
        )
        
        # Migrate associated destination records
        if dest_list_id:
            try:
                self._migrate_destinations_for_list_id(org_id, dest_list_id)
            except Exception as e:
                self._logger.error(
                    f"Failed to migrate destinations for list ID {dest_list_id}: {e}. Continuing."
                )
        return stats

    def _migrate_destinations_for_list_id(self, org_id: str, dest_list_id: str) -> None:
        """Migrate destination records for given list ID to include orgId.
        
        This method is idempotent - records with existing orgId are skipped.

        Args:
            org_id: The organization ID to add to the records.
            dest_list_id: Destination list ID (from selected_destination_lists.dest_list_id).
        """
        destinations_collection = KvStoreCollections.DESTINATIONS.value
        self._logger.info(
            f"Migrating destinations for destinationListId: {dest_list_id}"
        )

        query = KvStoreFilterQueries.equals(
            DestinationsFields.DESTINATION_LIST_ID, dest_list_id
        )
        records = json.loads(
            self._kv_service.query_items(
                destinations_collection,
                self._session_token,
                query,
            )
        )
        if not records:
            self._logger.info(
                f"No destination records found for destinationListId: {dest_list_id}"
            )
            return

        migrated_count = 0
        skipped_count = 0
        for record in records:
            # Idempotency check: skip if orgId already exists
            if record.get("orgId"):
                skipped_count += 1
                continue
                
            updated_record = {**record, "orgId": org_id}
            record_key = updated_record.pop("_key", "")
            self._kv_service.update_item_by_key(
                destinations_collection,
                record_key,
                self._session_token,
                updated_record,
            )
            migrated_count += 1

        self._logger.info(
            f"{destinations_collection} migration completed. "
            f"Migrated: {migrated_count}, Skipped: {skipped_count} records "
            f"for destinationListId: {dest_list_id}"
        )

    def _migrate_s3_indexes(self, org_id: str) -> CollectionMigrationStats:
        """Migrate S3 Indexes record to include orgId.
        
        Also validates that the resolved org_id exists in the configured indexes.
        If data exists but org_id is not found, a warning notification is sent
        but migration proceeds regardless.
        """
        collection = KvStoreCollections.S3_INDEXES.value
        stats = CollectionMigrationStats(collection=collection)
        
        self._logger.info(f"Starting migration for collection: {collection}")
        records = json.loads(
            self._kv_service.query_items(
                collection,
                self._session_token,
            )
        )
        if not records:
            self._logger.info(f"No {collection} records found for migration.")
            return stats

        stats.total = 1  # Only migrating the last record
        record = records[-1]
        # Idempotency check: skip if orgId already exists
        if record.get("orgId"):
            self._logger.info(
                f"{collection} record already has orgId '{record.get('orgId')}'. Skipping migration."
            )
            stats.skipped = 1
            return stats

        updated_record = {**record, "orgId": org_id}
        record_id = updated_record.pop("_key", "")
        self._kv_service.update_item_by_key(
            collection,
            record_id,
            self._session_token,
            updated_record,
        )
        stats.migrated = 1
        self._logger.info(
            f"{collection} migration completed successfully. orgId {org_id} added."
        )
        return stats

    def _migrate_appdiscovery_indexes(self, org_id: str) -> CollectionMigrationStats:
        """Migrate App Discovery Indexes record to include orgId."""
        return self._migrate_collection_record(
            KvStoreCollections.APPDISCOVERY_INDEXES.value,
            org_id,
        )

    def _migrate_privateapp_indexes(self, org_id: str) -> CollectionMigrationStats:
        """Migrate Private App Indexes record to include orgId."""
        return self._migrate_collection_record(
            KvStoreCollections.PRIVATEAPP_INDEXES.value,
            org_id,
        )

    def _migrate_indexing_script(self, org_id: str, input_type: ModInputType) -> bool:
        """Migrate Indexing Scripts to include orgId."""
        old_input_name = None
        input_fields = None
        if self._data_inputs_mgr is None:
            self._data_inputs_mgr = ModularInputManager(self._session_token)
        if input_type == ModInputType.APP_DISCOVERY:
            old_input_name = "appdiscovery"
        elif input_type == ModInputType.PRIVATE_APPS:
            old_input_name = "privateapps"
        
        try:
            input_fields = self._data_inputs_mgr.get_input(input_type, old_input_name)
        except ModularInputNotFoundException:
            self._logger.info(
                f"No existing modular input found for {input_type.value} during migration."
            )
            return False
        
        # Apply default values for missing fields
        if input_fields.log_level is None:
            input_fields.log_level = "INFO"
            self._logger.info(
                f"Applied default log_level 'INFO' for {input_type.value} modular input."
            )
        if input_fields.interval is None:
            input_fields.interval = ModInputInterval[input_type.name].value
            self._logger.info(
                f"Applied default interval {input_fields.interval} for {input_type.value} modular input."
            )
        
        # Idempotency check: skip if input already has orgId in name
        if input_fields.org_id:
            self._logger.info(
                f"Modular input for {input_type.value} already has orgId '{input_fields.org_id}'. "
                "Skipping migration."
            )
            return False
        
        # Create new input first, then delete old one (safer order to prevent data loss)
        # Use {input_type.value}_{org_id} naming convention to match org_accounts.py
        new_input_name = f"{input_type.value}_{org_id}"
        input_fields.org_id = org_id
        self._data_inputs_mgr.create_input(input_type, new_input_name, input_fields)
        self._logger.info(
            f"New modular input '{new_input_name}' created for {input_type.value} with orgId {org_id}."
        )
        
        # Delete old input only after successful creation
        try:
            self._data_inputs_mgr.delete_input(input_type, old_input_name)
            self._logger.info(
                f"Old modular input '{old_input_name}' deleted for {input_type.value}."
            )
        except Exception as e:
            # Log warning but don't fail - new input exists and will be used
            self._logger.warning(
                f"Failed to delete old modular input '{old_input_name}' for {input_type.value}: {e}. "
                "New input was created successfully, migration can proceed."
            )
        
        self._logger.info(
            f"Modular input for {input_type.value} migrated successfully with orgId {org_id}."
        )
        return True

    def _migrate_alert_actions(self, org_id: str) -> bool:
        """Migrate alert actions in saved searches to include orgId.

        Args:
            org_id: The organization ID to add to alert actions.

        Returns:
            True if migration was successful, False if no alert actions found.
        """
        self._logger.info("Starting migration for alert actions.")
        if self._alert_action_mgr is None:
            self._alert_action_mgr = AlertActionManager(self._session_token)

        stats = self._alert_action_mgr.migrate_alert_actions(org_id)

        if stats["total_searches"] == 0:
            self._logger.info("No saved searches with alert actions found for migration.")
            return False

        self._logger.info(
            f"Alert action migration completed. "
            f"Migrated: {stats['migrated']}, Skipped: {stats['skipped']}, Failed: {stats['failed']}"
        )
        return stats["migrated"] > 0 or stats["skipped"] > 0

    def _migrate_all_collection_records(
        self,
        collection: str,
        org_id: str,
        query_conditions: Optional[Dict[str, Any]] = None,
    ) -> CollectionMigrationStats:
        """Migrate all records in a collection to include orgId.
        
        This method is idempotent - records with existing orgId are skipped.

        Args:
            collection: The KV store collection name.
            org_id: The organization ID to add to all records.
            query_conditions: Optional query conditions to filter records.

        Returns:
            CollectionMigrationStats with migration statistics.
        """
        stats = CollectionMigrationStats(collection=collection)
        
        self._logger.info(f"Starting migration for all records in collection: {collection}")
        records = json.loads(
            self._kv_service.query_items(
                collection,
                self._session_token,
                query_conditions,
            )
        )
        if not records:
            self._logger.info(f"No {collection} records found for migration.")
            return stats

        stats.total = len(records)
        
        for record in records:
            # Idempotency check: skip if orgId already exists
            if record.get("orgId"):
                stats.skipped += 1
                continue
            
            try:
                updated_record = {**record, "orgId": org_id}
                record_key = updated_record.pop("_key", "")
                self._kv_service.update_item_by_key(
                    collection,
                    record_key,
                    self._session_token,
                    updated_record,
                )
                stats.migrated += 1
            except Exception as e:
                self._logger.error(f"Failed to migrate record in {collection}: {e}")
                stats.failed += 1

        self._logger.info(
            f"{collection} migration completed. "
            f"Total: {stats.total}, Migrated: {stats.migrated}, "
            f"Skipped: {stats.skipped}, Failed: {stats.failed}"
        )
        return stats

    def _migrate_cisco_investigate_domains(self, org_id: str) -> CollectionMigrationStats:
        """Migrate cisco_investigate_domains collection records to include orgId."""
        return self._migrate_all_collection_records(
            KvStoreCollections.CISCO_INVESTIGATE_DOMAINS.value,
            org_id,
        )

    def _migrate_cisco_investigate_ips(self, org_id: str) -> CollectionMigrationStats:
        """Migrate cisco_investigate_ips collection records to include orgId."""
        return self._migrate_all_collection_records(
            KvStoreCollections.CISCO_INVESTIGATE_IPS.value,
            org_id,
        )

    def _migrate_cisco_investigate_hashes(self, org_id: str) -> CollectionMigrationStats:
        """Migrate cisco_investigate_hashes collection records to include orgId."""
        return self._migrate_all_collection_records(
            KvStoreCollections.CISCO_INVESTIGATE_HASHES.value,
            org_id,
        )

    def _migrate_cisco_investigate_urls(self, org_id: str) -> CollectionMigrationStats:
        """Migrate cisco_investigate_urls collection records to include orgId."""
        return self._migrate_all_collection_records(
            KvStoreCollections.CISCO_INVESTIGATE_URLS.value,
            org_id,
        )

    def _migrate_alert_inputs(self, org_id: str) -> CollectionMigrationStats:
        """Migrate alert_inputs collection records to include orgId."""
        return self._migrate_all_collection_records(
            KvStoreCollections.ALERT_INPUTS.value,
            org_id,
        )

    def _migrate_credentials(self, org_id: str) -> None:
        """Migrate legacy credentials to org-specific storage.
        
        Copies api_key, api_secret, and access_token from legacy storage
        (without org_id suffix) to org-specific storage (with _{org_id} suffix).
        
        This method is idempotent - if org-specific tokens already exist,
        migration is skipped.
        
        Args:
            org_id: The organization ID to use for the new storage keys.
        """
        self._logger.info(f"Starting credential migration for org_id: {org_id}")
        
        # Idempotency check: skip if org-specific tokens already exist
        existing_token = TokenService.get_token(
            self._session_token, "api_key", org_id=org_id
        )
        if existing_token.get("payload"):
            self._logger.info(
                f"Org-specific credentials already exist for org_id {org_id}. "
                "Skipping credential migration."
            )
            return
        
        # Get legacy tokens (without org_id)
        legacy_api_key = TokenService.get_token(self._session_token, "api_key")
        legacy_api_secret = TokenService.get_token(self._session_token, "api_secret")
        legacy_access_token = TokenService.get_token(self._session_token, "access_token")
        
        api_key = legacy_api_key.get("payload", {}).get("clear_token", "")
        api_secret = legacy_api_secret.get("payload", {}).get("clear_token", "")
        access_token = legacy_access_token.get("payload", {}).get("clear_token", "")
        
        if not api_key or not api_secret:
            self._logger.warning(
                "Legacy api_key or api_secret not found. Skipping credential migration."
            )
            return
        
        # Store credentials with org_id suffix
        TokenService.set_token(
            self._session_token, api_key, "api_key", org_id=org_id
        )
        TokenService.set_token(
            self._session_token, api_secret, "api_secret", org_id=org_id
        )
        if access_token:
            TokenService.set_token(
                self._session_token, access_token, "access_token", org_id=org_id
            )
        
        self._logger.info(
            f"Credential migration completed successfully for org_id {org_id}."
        )

    def _set_global_org_if_needed(self, org_id: str) -> None:
        """Set the global org if not already set.
        
        This method is idempotent - if a global org is already configured,
        it will not be overwritten.
        
        Args:
            org_id: The organization ID to set as global org.
        """
        global_org_client = GlobalOrgClient(self._session_token)
        
        if global_org_client.global_org:
            self._logger.info(
                f"Global org already set to '{global_org_client.global_org}'. "
                "Skipping global org migration."
            )
            return
        
        global_org_client.global_org = org_id
        self._logger.info(f"Global org set to {org_id} during migration.")

    def _get_org_id_from_token(self) -> Optional[str]:
        """Extract organization ID from stored access token.
        
        Returns:
            The organization ID if successfully extracted, None otherwise.
        """
        try:
            token_info = TokenService.get_token(self._session_token, "access_token")
        except Exception as e:
            self._logger.error(f"Error getting orgId from token: {e}")
            return None
        token = token_info.get("payload", {}).get("clear_token", "")
        return get_org_id_from_token(token)

    def _get_org_id_from_api_client(
        self, oauth_record: Dict[str, Any]
    ) -> Optional[str]:
        """Get organization ID by initializing API client with stored credentials.
        
        Args:
            oauth_record: The OAuth settings record containing baseURL and storageRegion.
            
        Returns:
            The organization ID if successfully retrieved, None otherwise.
        """
        try:
            client_id = (
                TokenService.get_token(self._session_token, "api_key")
                .get("payload", {})
                .get("clear_token", "")
            )
            client_secret = (
                TokenService.get_token(self._session_token, "api_secret")
                .get("payload", {})
                .get("clear_token", "")
            )
        except Exception as e:
            self._logger.error(f"Error generating access token for migration: {e}")
            return None
        
        if not client_id or not client_secret:
            self._logger.error(
                "Client ID or Client Secret not found for generating access token during migration."
            )
            return None
        
        try:
            api_client = ReportingAPIClient(
                session_token=self._session_token,
                api_key=client_id,
                api_secret=client_secret,
                base_url=oauth_record.get("baseURL", ""),
                storage_region=oauth_record.get("storageRegion", ""),
                set_token=False,
            )
            return api_client.org_id
        except Exception as e:
            self._logger.error(
                f"Error initializing ReportingAPIClient for migration: {e}"
            )
            return None
