# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
from typing import Any, Dict, List, Optional

sys.path.append(dirname(abspath(__file__)))

import json
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from logger import Logger
from common import Common

from enums import (
    KvStoreCollections,
    KvStoreFilterQueries,
)
from enums import OAuthSettingsStatus
from collections_schema import OAuthSettingsFields
from global_org_client import GlobalOrgClient

kv_service = None


class GlobalOrgAPI(PersistentServerConnectionApplication):
    """
    REST API handler for managing the global organization setting.

    This class provides endpoints for listing available organizations
    and setting the active global organization.
    It extends Splunk's PersistentServerConnectionApplication to handle REST API requests.

    The handler supports the following HTTP methods:
        - GET: List all organizations.
        - POST: Set the global organization ID.

    Note:
        For migration functionality, use the /org_migration endpoint instead.

    Attributes:
        OAUTH_COLLECTION (str): KV store collection name for OAuth settings.

    Example:
        The handler is invoked via Splunk's REST API:
        ```
        GET /servicesNS/nobody/cisco-cloud-security/global_org
        POST /servicesNS/nobody/cisco-cloud-security/global_org
        ```
    """

    OAUTH_COLLECTION = KvStoreCollections.OAUTH_SETTINGS.value

    def __init__(self, command_line, command_arg):
        """
        Initialize the GlobalOrgAPI REST API handler.

        Sets up the handler with default values for session management,
        KV store service, global org client, and logging.

        Args:
            command_line (str): The command line string passed by Splunk.
            command_arg (str): Additional command arguments passed by Splunk.
        """
        PersistentServerConnectionApplication.__init__(self)
        self._session_token = None
        self._kv_service = None
        self._global_org_client = None
        self._logger = Logger()

    def handle(self, in_string):
        """
        Handle incoming REST API requests and route to appropriate methods.

        Parses the incoming request, initializes required services, and routes
        the request to the appropriate handler method based on the HTTP method
        and query parameters.

        Args:
            in_string (str): JSON-encoded string containing the request parameters,
                including session information, HTTP method, query parameters,
                and payload.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Response data or error message.
                - status (int): HTTP status code.
        """
        self._logger.info("GlobalOrgAPI.handle() called - starting request processing")
        try:
            self._logger.info("GlobalOrgAPI: Parsing input string")
            params = Common().parse_in_string(in_string)
            self._session_token = params["session"]["authtoken"]
            self._logger.info("GlobalOrgAPI: Session token obtained, initializing KV service")
            self._init_kv_service()
            self._logger.info("GlobalOrgAPI: KV service initialized, creating GlobalOrgClient")
            self._global_org_client = GlobalOrgClient(self._session_token)
            method: str = params["method"]
            query_params = params.get("query", {})
            payload = json.loads(params.get("payload", "{}"))
            self._logger.info(f"GlobalOrgAPI: method={method}, query_params={query_params}")
            if method.lower() == "get":
                self._logger.info("GlobalOrgAPI: Routing to list_orgs()")
                return self.list_orgs(query_params)
            elif method.lower() == "post":
                self._logger.info("GlobalOrgAPI: Routing to set_global_org()")
                return self.set_global_org(payload)
            else:
                self._logger.info(f"GlobalOrgAPI: Method {method} not supported")
                return {"payload": {"message": "Method not supported"}, "status": 405}

        except Exception as e:
            self._logger.error("API: global_org_api, Exception : {0}".format(str(e)))
            return {"payload": {"message": str(e)}, "status": 500}

    def list_orgs(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List all available organizations and the current global organization.

        Retrieves all active organization records from the KV store. If no
        records are found, attempts to perform migration from legacy settings.
        Supports two output formats based on the format_output parameter.

        Args:
            query_params (Dict[str, Any]): Query parameters containing:
                - format_output (str, optional): If '1', returns data in entry
                    format suitable for Splunk dropdowns. Defaults to '0'.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Contains 'orgIds' list and 'globalOrgId', or
                    'entry' list with content objects if format_output='1'.
                - status (int): HTTP status code (200 for success, 500 for errors).
        """
        self._logger.info("GlobalOrgAPI.list_orgs() - starting")
        format_output = query_params.get("format_output", "0")
        self._logger.info("GlobalOrgAPI: Fetching org records from kvstore")
        records = self._list_orgs_records()
        self._logger.info(f"GlobalOrgAPI: Found {len(records) if records else 0} org records")
        if not records:
            self._logger.info(
                "No org records found in kvstore. Migration may be required."
            )
            return {
                "payload": {
                    "message": "No organizations found."
                },
                "status": 404,
            }
        self._logger.info(f"Active org id: {self._global_org_client.global_org}")
        if format_output == "1":
            self._logger.info("GlobalOrgAPI: Returning entry format response")
            return {
                "payload": {
                    "entry": [
                        {
                            "content": {
                                "orgId": record.get("orgId", ""),
                                "globalOrgId": self._global_org_client.global_org,
                            }
                        }
                        for record in records
                    ],
                },
                "status": 200,
            }
        else:
            self._logger.info("GlobalOrgAPI: Returning standard format response")
            return {
                "payload": {
                    "orgIds": [record.get("orgId", "") for record in records],
                    "globalOrgId": self._global_org_client.global_org,
                },
                "status": 200,
            }

    def set_global_org(self, payload: Dict[str, str]) -> Dict[str, Any]:
        """
        Set the global organization ID.

        Updates the global organization setting to the specified org ID.
        Validates that the organization exists before setting it as global.

        Args:
            payload (Dict[str, str]): Request payload containing:
                - orgId (str): The organization ID to set as global.
                - data (Dict, optional): Nested payload from frontend requests.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Success or error message.
                - status (int): HTTP status code (200 for success, 400/404 for errors).
        """
        payload = payload.get("data", payload)
        org_id = payload.get("orgId", "")
        if not org_id:
            return {
                "payload": {"message": "orgId is required to set global organization."},
                "status": 400,
            }
        if not self._get_org_record(org_id):
            return {
                "payload": {"message": f"Organization with orgId {org_id} not found."},
                "status": 404,
            }
        self._global_org_client.global_org = org_id
        return {
            "payload": {
                "message": f"Organization with orgId {org_id} is set as global successfully."
            },
            "status": 200,
        }

    def _list_orgs_records(self) -> List[Dict[str, Any]]:
        """
        Retrieve all active organization records from the KV store.

        Queries the OAuth settings collection for all records with
        active status.

        Returns:
            List[Dict[str, Any]]: List of active OAuth settings records,
                each containing organization configuration data.
        """
        query = KvStoreFilterQueries.ACTIVE_OAUTH_ORG_RECORD_QUERY
        records = json.loads(
            self._kv_service.query_items(
                self.OAUTH_COLLECTION,
                self._session_token,
                query,
            )
        )
        return records

    def _get_org_record(self, org_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific organization record by org ID.

        Queries the OAuth settings collection for an active record
        matching the provided organization ID.

        Args:
            org_id (str): The organization ID to look up.

        Returns:
            Optional[Dict[str, Any]]: The organization record if found,
                otherwise None.
        """
        query = {
            OAuthSettingsFields.ORG_ID.value: org_id,
            OAuthSettingsFields.STATUS.value: OAuthSettingsStatus.ACTIVE.value
        }
        records = json.loads(
            self._kv_service.query_items(
                self.OAUTH_COLLECTION,
                self._session_token,
                query,
            )
        )
        return records[-1] if records else None

    def _init_kv_service(self):
        """
        Initialize the KV store service singleton.

        Creates a new KVStoreService instance if one doesn't exist,
        or reuses the existing global instance for efficiency.
        """
        global kv_service
        if kv_service is None:
            kv_service = KVStoreService(session_token=self._session_token)
        self._kv_service = kv_service
