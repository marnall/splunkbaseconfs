from __future__ import annotations

import sys
import time
import traceback
from typing import Dict, List, Any, Optional, Generator

import ta_analyst1_declare  # noqa: F401
from solnlib.utils import is_true
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option
from splunklib.client import connect

from analyst1_logging import get_logger
from command_helper import CommandHelper
from splunk_client import SplunkAccess

from config_manager import TAAnalyst1Config
from analyst1_splunk_search_client import Analyst1SplunkSearchClient
from splunk_client.splunk_kvs_manager import SplunkKVSManager
from analyst1_indicator_sync.sync.sync_service import IndicatorSynchronizerService
from analyst1_indicator_sync.core.enums import SyncMode

# Test config manager in production Splunk environment
logger = get_logger("ta_analyst1_index_to_kv")

REDIRECT_TO_LOG_FILE_MSG = "See {} for more details.".format(
    "ta_analyst1_index_to_kv.log"
)

@Configuration()
class Analyst1IndexToKvCommand(EventingCommand):
    """Analyst1 index to KV command."""

    sync_id = Option(name="sync_id", require=False)
    sync_mode = Option(name="sync_mode", require=False)
    # explicit_indexes = Option(name="explicit_indexes", require=False)  # Optional for diagnostics

    is_first_invocation: bool = True
    start_time: Optional[float] = None
    logger: Optional[Any] = None
    helper: Optional[Any] = None

    def _write_error(self, msg: str) -> None:
        """Log error message to Splunk UI from where this custom command was triggered."""
        self.write_error("{} {}".format(msg, REDIRECT_TO_LOG_FILE_MSG))
        exit(1)
    
    def _validate_parameters(self) -> tuple[Optional[int], Optional[str]]:
        """Validate and parse command parameters.
        
        Returns:
            Tuple of (sync_id, sync_mode) if valid, or (None, None) for auto mode
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Check if parameters were provided - if so, both must be present
        if self.sync_id or self.sync_mode:
            # If one is provided, both must be provided
            if not (self.sync_id and self.sync_mode):
                raise ValueError("Both sync_id and sync_mode must be provided together, or neither")
            
            # Validate sync_id
            sync_id = int(self.sync_id)
            if sync_id <= 0:
                raise ValueError(f"sync_id must be a positive integer, got: {sync_id}")
            
            # Validate sync_mode
            sync_mode = str(self.sync_mode).lower()
            if sync_mode not in ["full", "diff"]:
                raise ValueError(f"sync_mode must be 'full' or 'diff', got: {sync_mode}")
            
            logger.info(f"Using explicit parameters | sync_id={sync_id} sync_mode={sync_mode}")
            return sync_id, sync_mode
        else:
            logger.info("No explicit parameters provided, will fetch syncs from checkpoint")
            return None, None
    
    def _check_skip_index_setting(self, helper: Any, sync_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """Check if KV API mode is enabled and return skip event if needed.
        
        Args:
            helper: Command helper instance
            sync_id: The sync_id if provided explicitly
            
        Returns:
            Skip event dictionary if KV API mode is enabled, None otherwise
        """
        skip_index_setting = helper.get_global_setting("skip_index")
        logger.info(f"Configuration check | skip_index={skip_index_setting}")
        
        if is_true(skip_index_setting):
            # KV API mode is enabled, this command shouldn't be used
            error_message = (
                "Index-to-KV sync cannot run: KV API mode is currently enabled. "
                "To use this command, please configure the TA to use Index mode by: "
                "1) Setting 'Lookup creation mode' to 'Index' in the TA configuration, "
                "2) Ensuring all desired indexes are specified in the 'Indicator Indices' setting, "
                "3) Re-running the sync to populate indexes before using this command."
            )
            logger.warning(f"Sync skipped - KV API mode enabled | message={error_message}")
            
            return {
                "_time": time.time(),
                "command": "analyst1indextokv",
                "status": "skipped",
                "source_sync_id": sync_id if sync_id else "auto",
                "skip_index_setting": skip_index_setting,
                "message": error_message
            }
        
        return None

    def _execute_single_sync(
        self,
        sync_id: int,
        sync_mode: str,
        helper: Any,
        splunk_access: Any
    ) -> Dict[str, Any]:
        """Execute a single index-to-KV synchronization.
        
        Args:
            sync_id: The sync ID to process
            sync_mode: The sync mode (full/diff)
            helper: Command helper instance
            splunk_access: SplunkAccess instance with KV store manager
            
        Returns:
            Dictionary containing sync statistics
            
        Raises:
            Exception: If sync fails
        """
        logger.info(f"Starting index-to-KV sync | sync_id={sync_id} sync_mode={sync_mode}")
        start_time = time.time()
        
        try:
            # Create sync service for this specific sync
            # Convert lowercase sync_mode string to SyncMode enum
            sync_mode_enum = SyncMode.FULL if sync_mode == "full" else SyncMode.DIFF
            
            sync_service = IndicatorSynchronizerService(
                helper=helper,
                splunk_access=splunk_access,
                event_writer=None,  # Not needed for KV sync
                sync_mode=sync_mode_enum,  # Use the sync mode from parameter
                ioc_source_type="splunk_index",  # Use index as source
                target_sync_id=str(sync_id)     # Target specific sync_id
            )
            
            logger.debug(f"Created sync service | sync_id={sync_id} sync_mode={sync_mode_enum} source_type=splunk_index")
            
            # Force KV sync path for index-to-KV operations
            sync_service.skip_index = True
            logger.debug("Forced KV sync path (skip_index=True)")
            
            # Execute sync for common indicator types
            indicator_types = ["domain", "ip", "file", "url", "email", "httpRequest", "string", "mutex"]
            logger.info(f"Syncing indicator types: {', '.join(indicator_types)}")
            
            stats = sync_service.sync(indicator_types=indicator_types)
            
            duration = time.time() - start_time
            logger.info(
                f"Sync completed successfully | sync_id={sync_id} "
                f"duration={duration:.2f}s "
                f"created={stats.get('indicators_created', 0)} "
                f"updated={stats.get('indicators_updated', 0)} "
                f"deleted={stats.get('indicators_deleted', 0)}"
            )
            logger.debug(f"Full sync stats | sync_id={sync_id} stats={stats}")
            
            return stats
            
        except Exception as e:
            logger.error(
                f"Sync failed | sync_id={sync_id} error={str(e)}", 
                exc_info=True
            )
            raise

    def transform(self, events: Any) -> Generator[Dict[str, Any], None, None]:
        """Transform method of Eventing Command.
        
        Args:
            events: Input events (not used in this command)
            
        Yields:
            Dictionary events containing sync status information
        """
        logger.debug("Starting transform method")
        
        # Validate and parse command parameters
        try:
            sync_id, sync_mode = self._validate_parameters()
        except (ValueError, TypeError) as e:
            error_msg = f"Invalid command parameters: {str(e)}"
            logger.error(error_msg)
            
            # Return error event to user
            error_event = {
                "_time": time.time(),
                "command": "analyst1indextokv",
                "status": "error",
                "error": str(e),
                "message": error_msg
            }
            yield error_event
            return
        
        service = connect(
            token=self.search_results_info.auth_token,
            owner=self.metadata.searchinfo.username,
            app=self.metadata.searchinfo.app or "search",
            sharing="app"
        )
        logger.debug(f"Connected to Splunk service | app={self.metadata.searchinfo.app}")
        
        # Create helper first as we might need it for checkpoint
        helper = CommandHelper(
            session_key=self.search_results_info.auth_token,
            command_name="analyst1_index_to_kv",
            splunk_uri=getattr(self.metadata.searchinfo, 'splunk_uri', 'https://localhost:8089')
        )
        logger.debug(f"Created CommandHelper | command_name=analyst1_index_to_kv")

        # Check if KV API mode is enabled
        skip_event = self._check_skip_index_setting(helper, sync_id)
        if skip_event:
            logger.info(f"Yielding skip event | event={skip_event}")
            yield skip_event
            return

        # Determine which syncs to process
        syncs: List[Dict[str, Any]] = []
        if sync_id and sync_mode:
            # Use explicit parameters
            syncs = [{"sync_id": sync_id, "sync_mode": sync_mode}]
            logger.info(f"Using explicit sync | sync_id={sync_id} sync_mode={sync_mode}")
        else:
            # Fetch syncs from checkpoint
            last_sync_id = helper.get_check_point("analyst1_index_to_kv_last_sync_id")
            logger.debug(f"Retrieved checkpoint | last_sync_id={last_sync_id}")
            
            # Need to determine a sync_id for the search client
            # If no checkpoint, start from 0
            search_sync_id = last_sync_id if last_sync_id else 0
            
            # Create search client for fetching completed syncs
            a1_ssc = Analyst1SplunkSearchClient(
                service=service,
                sync_id=search_sync_id,
                earliest_time="-48h"
            ) # TODO - Determine if earliest_time should be configurable
            logger.debug(f"Created Analyst1SplunkSearchClient | sync_id={search_sync_id} earliest_time=-48h")
            
            syncs = a1_ssc.get_completed_syncs(since_sync_id=last_sync_id)
            logger.info(f"Fetched syncs from search | count={len(syncs)} since_id={last_sync_id}")
            if syncs:
                logger.debug(f"Sync list details | syncs={syncs}")
            else:
                logger.info("No pending syncs to process")
                no_sync_event = {
                    "_time": time.time(),
                    "command": "analyst1indextokv",
                    "status": "no_pending_syncs",
                    "message": f"No pending syncs found since last_sync_id={last_sync_id}. All syncs are up to date.",
                    "last_sync_id": helper.get_check_point("analyst1_index_to_kv_last_sync_id") or "none"
                }
                yield no_sync_event
                return


        # Create proper SplunkAccess object with KV store manager
        session_key = helper.context_meta.get("session_key")
        logger.debug(f"Creating SplunkAccess | session_key={'present' if session_key else 'missing'}")
        splunk_access = SplunkAccess(session_key=session_key, helper=helper)

        # Force KV store manager initialization for index-to-KV operations
        if splunk_access.kvsm is None:
            logger.info("KV store manager initialization required")

            # Wait for KV store to be ready
            logger.debug("Waiting for KV store to be ready...")
            splunk_access.wait_for_kvstore_initialization()
            logger.debug("KV store is ready")

            # Initialize KV store manager
            splunk_access.kvsm = SplunkKVSManager(splunk_access)
            logger.info("KV store manager initialized successfully")
        else:
            logger.debug("KV store manager already initialized")
        
        # Process each sync
        processed_count: int = 0
        total_syncs: int = len(syncs)
        logger.info(f"Starting sync processing | total_syncs={total_syncs} | syncs={syncs}")
        
        for i, sync in enumerate(syncs, 1):
            sync_id = sync.get("sync_id", sync_id)
            sync_mode = sync.get("sync_mode", sync_mode)
            
            logger.info(f"Processing sync {i}/{total_syncs} | sync_id={sync_id} sync_mode={sync_mode}")

            # Execute index-to-KV synchronization
            try:
                stats = self._execute_single_sync(
                    sync_id=sync_id,
                    sync_mode=sync_mode,
                    helper=helper,
                    splunk_access=splunk_access
                )

                # Calculate total changes
                total_changes: int = (
                    stats.get("indicators_created", 0) +
                    stats.get("indicators_updated", 0) +
                    stats.get("indicators_deleted", 0)
                )
                logger.debug(f"Sync stats | total_changes={total_changes} stats={stats}")

                # Create summary event
                summary_event: Dict[str, Any] = {
                    "_time": time.time(),
                    "command": "analyst1indextokv",
                    "status": "success",
                    "sync_progress": f"{i}/{total_syncs}",
                    "source_sync_id": sync_id,  # The sync_id from the index we're reading from
                    "kv_sync_id": stats.get("sync_id"),  # The new sync_id generated for this KV sync operation
                    "sync_mode": stats.get("sync_mode", "FULL"),
                    "duration_seconds": stats.get("duration_seconds", 0),
                    "indicators_created": stats.get("indicators_created", 0),
                    "indicators_updated": stats.get("indicators_updated", 0),
                    "indicators_deleted": stats.get("indicators_deleted", 0),
                    "message": f"[{i}/{total_syncs}] Successfully synchronized {total_changes} indicators from index (sync_id={sync_id}) to KV stores (kv_sync_id={stats.get('sync_id')})"
                }
                logger.debug(f"Yielding success event | sync_id={sync_id}")
                yield summary_event
                
                processed_count += 1

                # Save checkpoint after successful sync
                helper.save_check_point(
                    "analyst1_index_to_kv_last_sync_id",
                    sync_id  # Store the sync_id we just processed
                )
                logger.info(f"Checkpoint saved | sync_id={sync_id}")

            except Exception as e:
                logger.error(f"Sync failed | sync_id={sync_id} error={str(e)}")
                logger.error(f"Full traceback:\n{traceback.format_exc()}")

                # Create error event
                error_event: Dict[str, Any] = {
                    "_time": time.time(),
                    "command": "analyst1indextokv",
                    "status": "error",
                    "sync_progress": f"{i}/{total_syncs}",
                    "source_sync_id": sync_id,  # The sync_id we tried to sync from
                    "error": str(e),
                    "message": f"[{i}/{total_syncs}] Index-to-KV synchronization failed for sync_id={sync_id}: {str(e)}"
                }
                logger.debug(f"Yielding error event | sync_id={sync_id}")
                yield error_event
                
                # Raise to stop processing remaining syncs (maintains order)
                logger.warning(f"Aborting remaining syncs | processed={processed_count}/{total_syncs}")
                raise
        
        logger.info(f"Transform completed | processed_syncs={processed_count}/{total_syncs}")
        return


dispatch(Analyst1IndexToKvCommand, sys.argv, sys.stdin, sys.stdout, __name__)
