"""
REST handler for cleaning up resources when an input is deleted.
Deletes both checkpoint and deduplication cache from KVStore.
"""

import traceback
import json

import import_declare_test

from solnlib import log
from solnlib.modular_input import checkpointer
from solnlib._utils import get_collection_data
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler


ADDON_NAME = "Border_Add_on_for_OutSystems_Logs"


class OutSystemsLogsDeleteHandler(AdminExternalHandler):
    """
    REST handler for input deletion cleanup.
    Removes checkpoint and deduplication cache when input is deleted.
    """
    
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo):
        try:
            AdminExternalHandler.handleList(self, confInfo)
        except Exception:
            # Collections may not exist yet - this is normal on first load
            pass

    def handleEdit(self, confInfo):
        try:
            AdminExternalHandler.handleEdit(self, confInfo)
        except Exception:
            # Collections may not exist yet - this is normal on first load
            pass

    def handleCreate(self, confInfo):
        try:
            AdminExternalHandler.handleCreate(self, confInfo)
        except Exception:
            # Collections may not exist yet - this is normal on first load
            pass

    def handleRemove(self, confInfo):
        """
        Called when an input is deleted from the UI.
        Cleans up checkpoint and deduplication cache.
        """
        log_filename = f"{ADDON_NAME.lower()}_delete"
        logger = log.Logs().get_logger(log_filename)
        session_key = self.getSessionKey()
        input_name = str(self.callerArgs.id)
        
        logger.info(f"🗑️ Deleting resources for input '{input_name}'")
        
        # Delete checkpoint
        try:
            checkpoint_key = f"{input_name}_opt_end_date"
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                collection_name="outsystems_logs_checkpoints",
                session_key=session_key,
                app=ADDON_NAME,
            )
            kvstore_checkpointer.delete(checkpoint_key)
            logger.info(f"✅ Deleted checkpoint for '{input_name}'")
        except Exception as e:
            logger.warning(f"Failed to delete checkpoint for '{input_name}': {e}")
            # Continue with dedup cache deletion even if checkpoint fails
        
        # Delete deduplication cache
        try:
            # Get collection data client
            dedup_collection = get_collection_data(
                collection_name="outsystems_dedup_cache",
                session_key=session_key,
                app=ADDON_NAME,
                owner="nobody"
            )
            
            # Delete all records for this input
            query = json.dumps({"input_name": input_name})
            dedup_collection.delete(query=query)
            logger.info(f"✅ Deleted deduplication cache for '{input_name}'")
        except Exception as e:
            logger.warning(f"Failed to delete dedup cache for '{input_name}': {e}")
            log.log_exception(
                logger,
                e,
                "Dedup Cache Cleanup Error",
                msg_before=f"Error while deleting dedup cache for {input_name}. {traceback.format_exc()}",
            )
        
        # Call parent to complete the deletion
        AdminExternalHandler.handleRemove(self, confInfo)
        logger.info(f"🏁 Completed deletion of '{input_name}'")

