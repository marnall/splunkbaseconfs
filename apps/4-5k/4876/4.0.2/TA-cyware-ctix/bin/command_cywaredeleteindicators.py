"""Delete expired indicators from KVStore lookups."""

import ta_cyware_ctix_declare  # noqa: F401

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration
import ta_cyware_ctix.logging_helper as logging_helper
from ta_cyware_ctix.kvstore_helper import CollectionManager, CollectionNotFoundError
from ta_cyware_ctix.constants import MASTER_LOOKUP_DICT, MATCHED_LOOKUP_DICT

import sys
import time
import traceback

logger = logging_helper.get_logger("delete_indicators")

# Static list of all lookups to process
MASTER_LOOKUPS = list(MASTER_LOOKUP_DICT.values())
MATCHED_LOOKUPS = list(MATCHED_LOOKUP_DICT.values())


@Configuration()
class CywareDeleteIndicatorsCommand(GeneratingCommand):
    """Splunk custom search command to delete expired indicators from all KVStore lookups."""

    def _delete_from_collection(self, collection_name, delete_query, current_time):
        """
        Delete expired indicators from a single collection.

        Args:
            collection_name: Name of the KVStore collection
            delete_query: Query to identify records to delete
            current_time: Current epoch time for logging

        Returns:
            dict: Result with collection name and status
        """
        try:
            collection_manager = CollectionManager(
                collection_name=collection_name,
                session_key=self.service.token
            )

            # Get count of records to delete before deletion
            records_to_delete = collection_manager.get(query=delete_query)
            delete_count = len(records_to_delete)

            if delete_count > 0:
                collection_manager.delete_batch(delete_query)
                logger.info(
                    f"Deleted {delete_count} expired indicators from {collection_name}"
                )
            else:
                logger.info(f"No expired indicators found in {collection_name}")

            return {
                "collection": collection_name,
                "status": "success",
                "deleted_count": delete_count,
                "current_time": current_time
            }

        except CollectionNotFoundError:
            logger.warning(f"Collection {collection_name} not found, skipping")
            return {
                "collection": collection_name,
                "status": "skipped",
                "deleted_count": 0,
                "message": "Collection not found",
                "current_time": current_time
            }

        except Exception as e:
            logger.error(
                f"Error deleting from {collection_name}: {str(e)}\n{traceback.format_exc()}"
            )
            return {
                "collection": collection_name,
                "status": "error",
                "deleted_count": 0,
                "message": str(e),
                "current_time": current_time
            }

    def generate(self):
        """Generate results by deleting expired indicators from all lookups."""
        logger.info("Starting deletion of expired indicators from all lookups")

        # Define current time ONCE before iteration to ensure consistent time across all lookups
        current_time = int(time.time())

        # Query for expired indicators:
        # - valid_until is less than current time
        # Simplified query format that Splunk KVStore supports
        delete_query = {"valid_until": {"$lt": current_time}}

        logger.info(f"Delete query: {delete_query}")
        logger.info(f"Current time for comparison: {current_time}")

        total_deleted = 0
        total_errors = 0

        all_lookups = MASTER_LOOKUPS + MATCHED_LOOKUPS
        logger.info(f"Processing {len(all_lookups)} master and matched lookups")

        for collection_name in all_lookups:
            result = self._delete_from_collection(collection_name, delete_query, current_time)
            if "cyware_ti_" in collection_name:
                result["lookup_type"] = "master"
            elif "cyware_matched_indicators_" in collection_name:
                result["lookup_type"] = "matched"
            else:
                result["lookup_type"] = "unknown"
            result["_time"] = time.time()

            if result["status"] == "success":
                total_deleted += result["deleted_count"]
            elif result["status"] == "error":
                total_errors += 1

            yield result

        logger.info(
            f"Deletion complete. Total deleted: {total_deleted}, Errors: {total_errors}"
        )


dispatch(CywareDeleteIndicatorsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
