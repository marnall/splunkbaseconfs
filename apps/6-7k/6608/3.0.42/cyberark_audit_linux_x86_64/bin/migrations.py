"""One-time migration for plugin major version upgrades (1.x -> 2.x)."""
import json
from typing import Any

from splunk_kv_store_db_services import UserConfiguration

# Migration is needed only when upgrading from 1.x to 2.x
# Once on 2.x, no further migration needed regardless of minor updates
MIGRATION_SCHEMA_VERSION = 2


class MigrationManager:
    """
    Manages one-time migration from legacy plugin (1.x) to new architecture (2.x).

    Migration runs only once when:
    - No migration version exists (fresh 1.x install being upgraded)
    - Migration version < MIGRATION_SCHEMA_VERSION

    Once migrated to 2.x, subsequent updates (2.1, 2.2, etc.) won't trigger migration.

    Safety Features:
    - Pre-validation before any changes
    - Legacy input preserved until migration fully verified
    - Detailed logging for troubleshooting
    - Graceful degradation (credentials/checkpoint failures don't block config migration)
    """

    METADATA_COLLECTION = 'cyberark_audit_metadata'
    MIGRATION_DOC_KEY = 'migration_state'

    def __init__(self, kv_store, secret_manager, logger, app_name: str):
        self._kv_store = kv_store
        self._secret_manager = secret_manager
        self._logger = logger
        self._app_name = app_name
        self._service = kv_store.service
        self._ensure_metadata_collection()

    def _ensure_metadata_collection(self):
        """Create metadata collection if it doesn't exist."""
        try:
            if self.METADATA_COLLECTION not in self._service.kvstore:
                self._service.kvstore.create(self.METADATA_COLLECTION)
                self._logger.info(f'Created metadata collection: {self.METADATA_COLLECTION}')
        except Exception as e:
            self._logger.error(f'Failed to create metadata collection: {e}')

    # ─────────────────────────────────────────────────────────────────────────
    # Migration State Management
    # ─────────────────────────────────────────────────────────────────────────

    def _get_migration_version(self) -> int | None:
        """Get the current migration version from KV Store.

        Returns:
            int: Migration version if found
            None: No version exists (fresh install, never migrated)
        """
        try:
            collection = self._service.kvstore[self.METADATA_COLLECTION]
            doc = collection.data.query_by_id(self.MIGRATION_DOC_KEY)
            return int(doc.get('version', 0))
        except Exception:
            return None

    def _set_migration_version(self, version: int):
        """Update the migration version in KV Store."""
        try:
            collection = self._service.kvstore[self.METADATA_COLLECTION]
            data = {
                '_key': self.MIGRATION_DOC_KEY,
                'version': version,
                'app_name': self._app_name,
            }

            try:
                collection.data.query_by_id(self.MIGRATION_DOC_KEY)
                collection.data.update(id=self.MIGRATION_DOC_KEY, data=data)
            except Exception:
                collection.data.insert(data=json.dumps(data))

            self._logger.info(f'Migration schema version set to {version}')
        except Exception as e:
            self._logger.error(f'Failed to set migration version: {e}')
            raise

    def _get_legacy_inputs(self) -> dict:
        """
        Get the ACTIVE legacy input from inputs.conf if it exists.

        Note: 1.x plugin only supports single tenant, so we only migrate
        the one enabled input. Multiple stanzas may exist (disabled, test configs),
        but only one should be active (disabled=0 or disabled=false).

        Returns:
            Dict with single active input, or empty dict if none found
        """
        try:
            for input_item in self._service.inputs.list():
                input_config = self._extract_valid_legacy_input(input_item)
                if input_config:
                    return {input_item.name: input_config}
            return {}
        except Exception as e:
            self._logger.warning(f'Could not read legacy inputs: {e}')
            return {}

    def _extract_valid_legacy_input(self, input_item) -> dict | None:
        """Extract and validate a legacy input. Returns config dict or None if invalid."""
        # Only process inputs from this app
        if not (input_item.name and self._app_name in str(input_item.path)):
            return None

        input_config = dict(input_item.content)

        # Check if input is enabled
        is_disabled = input_config.get('disabled', '0')
        if str(is_disabled).lower() in ('1', 'true'):
            self._logger.info(f'Skipping disabled input: {input_item.name}')
            return None

        # Check if this is a valid CyberArk audit input
        device_name = input_config.get('device_name', '')
        if not device_name:
            self._logger.warning(f'Skipping input without device_name: {input_item.name}')
            return None

        self._logger.info(f'Found active legacy input: {input_item.name} (device: {device_name})')
        return input_config

    def needs_migration(self) -> bool:
        """
        Check if migration is needed (1.x -> 2.x upgrade).

        Returns False if:
        - Already on 2.x (no migration needed for 2.1, 2.2, etc.)
        - Fresh install (no legacy inputs exist)
        """
        stored_version = self._get_migration_version()

        # Already migrated to 2.x or higher
        if stored_version is not None and stored_version >= MIGRATION_SCHEMA_VERSION:
            self._logger.info(f'Migration check: stored_version={stored_version}, '
                              f'schema_version={MIGRATION_SCHEMA_VERSION}, needs_migration=False (already migrated)')
            return False

        # Check if this is a fresh install (no legacy inputs)
        if stored_version is None:
            legacy_inputs = self._get_legacy_inputs()
            if not legacy_inputs:
                # Fresh install - no migration needed, mark as v2
                self._logger.info('Migration check: Fresh install detected (no legacy inputs), marking as v2')
                try:
                    self._set_migration_version(MIGRATION_SCHEMA_VERSION)
                except Exception as e:
                    self._logger.warning(f'Could not set migration version on fresh install: {e}')
                return False
            else:
                # Legacy inputs exist - need migration
                self._logger.info(f'Migration check: stored_version=None, found {len(legacy_inputs)} legacy inputs, needs_migration=True')
                return True

        # Version exists but is < 2 - need migration
        needs = stored_version < MIGRATION_SCHEMA_VERSION
        self._logger.info(f'Migration check: stored_version={stored_version}, '
                          f'schema_version={MIGRATION_SCHEMA_VERSION}, needs_migration={needs}')
        return needs

    def _validate_migration_prerequisites(self, params: dict) -> tuple[bool, list[str]]:
        """
        Pre-validate that migration can succeed before making any changes.

        Returns:
            (can_proceed, warnings): Tuple of success flag and list of warnings
        """
        warnings = []
        device_name = params.get('device_name')

        # Check required fields
        required = ['device_name', 'auth_endpoint', 'api_endpoint', 'api_region']
        missing = [f for f in required if not params.get(f)]
        if missing:
            warnings.append(f"Device '{device_name}': Missing required fields: {missing}")
            self._log_warnings(warnings)
            return False, warnings

        # Check credentials (warn but don't block)
        cred_warning = self._check_credentials_exist(device_name)
        if cred_warning:
            warnings.append(cred_warning)

        self._log_warnings(warnings)
        return True, warnings

    def _log_warnings(self, warnings: list[str]):
        """Log migration pre-check warnings."""
        for warning in warnings:
            self._logger.warning(f'Migration pre-check: {warning}')

    def _check_credentials_exist(self, device_name: str) -> str | None:
        """Check if legacy credentials exist. Returns warning message if not."""
        try:
            cert = self._secret_manager.get_secret('certificate')
            pkey = self._secret_manager.get_secret('pkey')
            if not cert or not pkey:
                return f"Device '{device_name}': Credentials incomplete - will need manual re-entry"
        except Exception:
            return f"Device '{device_name}': Could not read credentials - will need manual re-entry"
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Migration Execution
    # ─────────────────────────────────────────────────────────────────────────

    def run_migration(self) -> bool:
        """
        Run migration from 1.x to 2.x if needed.

        Returns True if migration succeeded or was not needed.

        Safety guarantees:
        - Pre-validates before making changes
        - Legacy input only deleted after config successfully saved to KV Store
        - Credential/checkpoint failures are logged but don't block migration
        """
        if not self.needs_migration():
            self._logger.info('Already on 2.x schema - no migration needed')
            return True

        self._logger.info('Starting migration from 1.x to 2.x')

        try:
            legacy_inputs = self._get_legacy_inputs()

            if legacy_inputs:
                input_name, params = next(iter(legacy_inputs.items()))

                # Pre-validate before making any changes
                can_proceed, _ = self._validate_migration_prerequisites(params)
                if not can_proceed:
                    self._logger.error('Please fix the issues above and restart. No changes were made.')
                    return False

                self._logger.info(f'Migrating legacy integration: {input_name}')

                if not self._migrate_single_integration(input_name, params):
                    self._logger.error('Migration failed - manual intervention may be required')
                    return False
            else:
                self._logger.info('No legacy inputs found - fresh install or already cleaned up')

            # Mark migration complete
            self._set_migration_version(MIGRATION_SCHEMA_VERSION)
            self._logger.info('Migration to 2.x completed successfully')
            return True

        except Exception as e:
            self._logger.error(f'Migration failed: {e}', exc_info=True)
            return False

    def _migrate_single_integration(self, input_name: str, params: dict) -> bool:
        """
        Migrate a single legacy integration to KV Store.

        Order of operations (safe):
        1. Create KV Store config
        2. Verify KV Store config exists
        3. Migrate credentials
        4. Migrate checkpoint
        5. ONLY THEN delete legacy input

        Returns True if config migration succeeded.
        """
        device_name = params.get('device_name')
        display_name = input_name.split('://')[-1] if '://' in input_name else device_name

        # Skip if already migrated
        if self._kv_store.get_user_config(device_name):
            self._logger.info(f'Device {device_name} already exists in KV Store - skipping')
            return True

        try:
            self._logger.info(f'Step 1/4: Creating config for {device_name}')
            if not self._create_and_verify_config(params, display_name, device_name):
                return False

            self._logger.info(f'Step 2/4: Migrating credentials for {device_name}')
            self._migrate_credentials(device_name)

            self._logger.info(f'Step 3/4: Migrating checkpoint for {device_name}')
            self._migrate_checkpoint(device_name)

            self._logger.info(f'Step 4/4: Cleaning up legacy input for {device_name}')
            self._cleanup_legacy_input(input_name, device_name)

            self._logger.info(f'Successfully migrated device: {device_name}')
            return True

        except Exception as e:
            self._logger.error(f'Failed to migrate device {device_name}: {e}', exc_info=True)
            return False

    def _create_and_verify_config(self, params: dict, display_name: str, device_name: str) -> bool:
        """Create KV Store config and verify it was saved. Returns True on success."""
        config = self._build_user_configuration(params, display_name)
        self._kv_store.create_user_config(config)

        if not self._kv_store.get_user_config(device_name):
            self._logger.error(f'Config creation failed - verification did not find device {device_name}')
            return False

        self._logger.info(f'Config migrated and verified for device: {device_name}')
        return True

    def _migrate_checkpoint(self, device_name: str) -> bool:
        """
        Migrate legacy checkpoint to new device-specific format.

        Returns True if checkpoint was migrated successfully.
        """
        try:
            # Legacy collection name pattern
            legacy_collection_name = f'{self._app_name}_collection'
            legacy_doc_id = f'{legacy_collection_name}_state_doc_id'

            collection = self._service.kvstore[legacy_collection_name]
            legacy_doc = collection.data.query_by_id(legacy_doc_id)

            if legacy_doc:
                next_page_cursor = legacy_doc.get('next_page_cursor', '')
                if next_page_cursor:
                    self._kv_store.update_user_checkpoint(device_name, next_page_cursor)
                    self._logger.info(f'Migrated checkpoint for device: {device_name}')

                    # Optionally delete the legacy checkpoint doc
                    try:
                        collection.data.delete_by_id(legacy_doc_id)
                        self._logger.info(f'Deleted legacy checkpoint document: {legacy_doc_id}')
                    except Exception as e:
                        self._logger.warning(f'Could not delete legacy checkpoint: {e}')
                    return True
                else:
                    self._logger.info(f'No checkpoint cursor found for migration')
                    return True  # No checkpoint to migrate is still success
            else:
                self._logger.info(f'No legacy checkpoint found - starting fresh')
                return True  # No checkpoint to migrate is still success

        except Exception as e:
            self._logger.warning(f'Could not migrate checkpoint: {e}')
            return False

    @staticmethod
    def _build_user_configuration(params: dict[str, Any], display_name: str) -> UserConfiguration:
        """Build UserConfiguration from migration parameters."""
        device_name = params.get('device_name')

        services_filter = params.get('services_filter', 'All')
        if services_filter == 'ALL':
            services_filter = 'All'

        index_name = params.get('index_name', 'main')
        if index_name == 'default':
            index_name = 'main'

        return UserConfiguration(device_name=device_name, auth_endpoint=params['auth_endpoint'], api_endpoint=params['api_endpoint'],
                                 api_region=params['api_region'], services_filter=services_filter,
                                 initial_minutes_back_start=int(params.get('initial_minutes_back_start', 15)), index_name=index_name,
                                 integration_display_name=display_name or device_name, host=params.get('host', '$decideOnStartup'),
                                 sourcetype=params.get('sourcetype', 'cyberark:audit'), page_size=int(params.get('page_size', 500)))

    def _migrate_credentials(self, device_name: str) -> bool:
        """
        Migrate legacy credentials to device-specific format.

        Returns True if credentials were migrated successfully.
        """
        try:
            certificate = self._secret_manager.get_secret('certificate')
            private_key = self._secret_manager.get_secret('pkey')

            if not certificate or not private_key:
                self._logger.warning(f'Legacy credentials incomplete for device: {device_name}')
                return False

            self._secret_manager.save_user_credentials(device_name, certificate, private_key)
            self._logger.info(f'Migrated credentials for device: {device_name}')
            return True
        except ValueError as e:
            self._logger.warning(f'Legacy credentials not found for migration: {e}')
            return False
        except Exception as e:
            self._logger.warning(f'Failed to migrate credentials for {device_name}: {e}')
            return False

    def _cleanup_legacy_input(self, stanza_name: str, device_name: str):
        """Clean up legacy input stanza after migration."""
        # Verify migration first
        if not self._kv_store.get_user_config(device_name):
            self._logger.error(f'Cannot cleanup - config not found for device: {device_name}')
            return

        try:
            for input_item in self._service.inputs.list():
                if input_item.name == stanza_name or stanza_name.endswith(f'://{input_item.name}'):
                    self._logger.info(f'Deleting legacy input stanza: {input_item.name}')
                    input_item.delete()
                    return
            self._logger.warning(f'Input stanza not found: {stanza_name}')
        except Exception as e:
            self._logger.error(f'Failed to delete stanza {stanza_name}: {e}')
