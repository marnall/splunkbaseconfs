"""
History Cleanup Script
Removes old query history records based on license retention limits.
Run as a scheduled Splunk script.
"""
import sys
import os
import time
import logging
from datetime import datetime, timezone, timedelta

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from splunklib import client
from kv_store import KVStoreClient
from license_verifier import get_cached_license_status

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def get_license_limits(session_key):
    """Get license limits from the current license.

    Args:
        session_key: Splunk session key

    Returns:
        dict: License limits
    """
    default_limits = {
        'history_retention_days': 7
    }

    try:
        # Get server GUID
        service = client.connect(
            token=session_key,
            owner='nobody',
            app='AI_Query_Assistant_for_Splunk'
        )
        server_info = service.info
        server_guid = server_info.get('guid', '')

        # Get license key from storage/passwords
        passwords = service.storage_passwords
        license_key = None
        for password in passwords:
            if password.username == 'mcp_license_key':
                license_key = password.clear_password
                break

        if not license_key:
            logger.warning("No license key found, using default limits")
            return default_limits

        # Validate license
        result = get_cached_license_status(license_key, server_guid)
        if not result['valid']:
            logger.warning(f"License invalid: {result['error']}, using default limits")
            return default_limits

        license_data = result.get('data', {})
        license_type = license_data.get('license_type', 'starter')

        # Define limits by license type
        limits_by_type = {
            'starter': {'history_retention_days': 7},
            'professional': {'history_retention_days': 30},
            'enterprise': {'history_retention_days': 365}
        }

        return limits_by_type.get(license_type, default_limits)

    except Exception as e:
        logger.error(f"Failed to get license limits: {e}")
        return default_limits


def cleanup_old_history(session_key):
    """Remove history records older than the retention period.

    Args:
        session_key: Splunk session key

    Returns:
        int: Number of records deleted
    """
    try:
        limits = get_license_limits(session_key)
        retention_days = limits.get('history_retention_days', 7)

        # Calculate cutoff timestamp
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        cutoff_timestamp = int(cutoff_date.timestamp())

        logger.info(f"Cleaning up history older than {retention_days} days (before {cutoff_date.isoformat()})")

        # Connect to KV Store
        service = client.connect(
            token=session_key,
            owner='nobody',
            app='AI_Query_Assistant_for_Splunk'
        )
        kv_client = KVStoreClient(service, 'mcp_query_history')

        # Loop in batches: above ~10k stale records, a single query+delete
        # pass cannot catch up. Keep iterating until the query returns empty
        # or we hit a per-run safety cap so a runaway DB doesn't block forever.
        BATCH_LIMIT = 1000
        MAX_RUN_DELETIONS = 200000  # ~200 batches of 1000

        deleted_count = 0
        while deleted_count < MAX_RUN_DELETIONS:
            old_records = kv_client.query(
                {'timestamp': {'$lt': cutoff_timestamp}},
                limit=BATCH_LIMIT,
            )
            if not old_records:
                break
            batch_deleted = 0
            for record in old_records:
                try:
                    kv_client.delete(record['_key'])
                    deleted_count += 1
                    batch_deleted += 1
                except Exception as e:
                    logger.warning(f"Failed to delete record {record.get('_key')}: {e}")
            if batch_deleted == 0:
                # Avoid infinite loop if the same records keep coming back
                # because deletes silently fail.
                logger.warning("history_cleanup: batch made no progress, stopping")
                break

        if deleted_count >= MAX_RUN_DELETIONS:
            logger.warning("history_cleanup: hit per-run safety cap of %d", MAX_RUN_DELETIONS)
        logger.info(f"Deleted {deleted_count} old history records")
        return deleted_count

    except Exception as e:
        logger.error(f"Failed to cleanup history: {e}")
        return 0


if __name__ == '__main__':
    # Get session key from stdin (Splunk passes it this way)
    session_key = sys.stdin.readline().strip()

    if not session_key:
        logger.error("No session key provided")
        sys.exit(1)

    try:
        deleted = cleanup_old_history(session_key)
        logger.info("Cleanup completed: %d records deleted", deleted)
        sys.exit(0)
    except Exception as e:
        logger.exception("Cleanup script failed")
        sys.exit(1)
