# encoding = utf-8
"""
Global Org Collection Client

A lightweight utility client to manage the global org record in the
global_org KV store collection. Provides get/set operations using
an upsert pattern (single record).
"""

from __future__ import print_function

import sys
from os.path import dirname, abspath
from typing import Optional

sys.path.append(dirname(abspath(__file__)))

import json
from service.app_kvstore_service import KVStoreService
from enums import KvStoreCollections
from collections_schema import GlobalOrgFields
from logger import Logger


class GlobalOrgClient:
    """
    Client for managing the global org record in the global_org KV store collection.
    
    This client provides simple get/set operations for storing a single global
    organization ID. Uses an upsert pattern - setting global_org will replace any
    existing record with the new org ID.

    Usage:
        client = GlobalOrgClient(session_token)
        
        # Get global org
        org_id = client.global_org
        
        # Set global org
        client.global_org = "org-123"
    """

    COLLECTION = KvStoreCollections.GLOBAL_ORG.value

    def __init__(self, session_token: str):
        """
        Initialize the GlobalOrgClient.

        Args:
            session_token: The Splunk session authentication token.
        """
        self._session_token = session_token
        self._logger = Logger()
        self._kv_service = KVStoreService(session_token=session_token)

    @property
    def global_org(self) -> Optional[str]:
        """
        Get the global org ID from the collection.

        Returns:
            The org ID string if a record exists, None otherwise.
        """
        try:
            response = self._kv_service.query_items(
                self.COLLECTION,
                self._session_token
            )
            records = json.loads(response)
            if records and len(records) > 0:
                return records[0].get(GlobalOrgFields.ORG_ID.value)
            return None
        except Exception as e:
            self._logger.error(f"Error getting global org: {str(e)}")
            return None

    @global_org.setter
    def global_org(self, org_id: str) -> None:
        """
        Set the global org ID in the collection.

        This uses an upsert pattern - it deletes any existing records
        and inserts a new record with the provided org ID.

        Args:
            org_id: The organization ID to set as the global org.

        Raises:
            Exception: If the operation fails.
        """
        try:
            # Delete all existing records (upsert pattern - single record)
            self._kv_service.delete_all_items(self.COLLECTION, self._session_token)

            # Insert the new global org record
            record = {GlobalOrgFields.ORG_ID.value: org_id}
            self._kv_service.insert_record(self.COLLECTION, self._session_token, record)

            self._logger.info(f"Global org set to: {org_id}")
        except Exception as e:
            self._logger.error(f"Error setting global org: {str(e)}")
            raise

    def delete(self) -> bool:
        """
        Delete the global org record from the collection.

        Returns:
            True if the operation was successful, False otherwise.
        """
        try:
            self._kv_service.delete_all_items(self.COLLECTION, self._session_token)
            self._logger.info("Global org deleted")
            return True
        except Exception as e:
            self._logger.error(f"Error deleting global org: {str(e)}")
            return False
