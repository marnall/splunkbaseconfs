# encoding = utf-8
"""REST API handler for managing alert actions."""

from __future__ import print_function

import json
import sys
from os.path import dirname, abspath
from typing import Any, Dict

sys.path.append(dirname(abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common
from alert_action_manager import AlertActionManager
from service.app_kvstore_service import KVStoreService
from enums import KvStoreCollections


class AlertActionsAPI(PersistentServerConnectionApplication):
    """
    REST API handler for managing alert actions (saved searches with app's alert actions enabled).

    This class provides endpoints for deleting alert actions associated with
    a specific organization when the organization account is deleted.

    The handler supports the following HTTP methods:
        - DELETE: Delete all saved searches with app's alert actions for a specific org_id.

    Example:
        The handler is invoked via Splunk's REST API:
        ```
        DELETE /servicesNS/nobody/cisco-cloud-security/alert_actions?orgId=<org_id>
        ```
    """

    def __init__(self, command_line, command_arg):
        """
        Initialize the AlertActionsAPI REST API handler.

        Args:
            command_line (str): The command line string passed by Splunk.
            command_arg (str): Additional command arguments passed by Splunk.
        """
        PersistentServerConnectionApplication.__init__(self)
        self._session_token = None
        self._logger = Logger()

    def handle(self, in_string):
        """
        Handle incoming REST API requests and route to appropriate methods.

        Args:
            in_string (str): JSON-encoded string containing the request parameters,
                including session information, HTTP method, query parameters,
                and payload.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Response data or error message.
                - status (int): HTTP status code.
        """
        self._logger.info(
            "AlertActionsAPI.handle() called - starting request processing"
        )
        try:
            params = Common().parse_in_string(in_string)
            self._session_token = params["session"]["authtoken"]
            method: str = params["method"]
            query_params = params.get("query", {})

            self._logger.info(
                f"AlertActionsAPI: method={method}, query_params={query_params}"
            )

            if method.lower() == "delete":
                return self._delete_alert_actions(query_params)
            else:
                self._logger.info(f"AlertActionsAPI: Method {method} not supported")
                return {"payload": {"message": "Method not supported"}, "status": 405}

        except Exception as e:
            self._logger.error(f"API: alert_actions_api, Exception: {str(e)}")
            return {"payload": {"message": str(e)}, "status": 500}

    def _delete_alert_actions(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete all saved searches with app's alert actions for a specific organization.

        This method finds all saved searches that have any of the app's alert actions
        (block_destinations, investigate_destinations, investigate_reports) enabled
        and configured with the specified org_id, then deletes them.

        Args:
            query_params (Dict[str, Any]): Query parameters containing:
                - orgId (str): The organization ID whose alert actions should be deleted.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Contains 'deleted_count' and 'message'.
                - status (int): HTTP status code (200 for success, 400 for missing params,
                    500 for errors).
        """
        org_id = query_params.get("orgId")

        if not org_id:
            self._logger.error("AlertActionsAPI: orgId parameter is required")
            return {
                "payload": {"message": "orgId parameter is required"},
                "status": 400,
            }

        self._logger.info(
            f"AlertActionsAPI: Deleting alert actions for org_id={org_id}"
        )

        try:
            kv_service = KVStoreService(
                KvStoreCollections.SELECTED_DESTINATION_LISTS.value, self._session_token
            )
            dest_list_records = json.loads(
                kv_service.query_items(
                    KvStoreCollections.SELECTED_DESTINATION_LISTS.value,
                    self._session_token,
                    {"orgId": org_id},
                )
            )
            manager = AlertActionManager(session_key=self._session_token)
            all_saved_searches = []
            seen_names = set()

            org_saved_searches = manager.get_saved_searches_with_alert_actions(
                org_id=org_id
            )
            for ss in org_saved_searches:
                if ss.name not in seen_names:
                    all_saved_searches.append(ss)
                    seen_names.add(ss.name)
            self._logger.info(
                f"AlertActionsAPI: Found {len(org_saved_searches)} investigate alert actions for org_id={org_id}"
            )

            # Get destination list IDs for this org from selected_destination_lists

            dest_list_ids = [
                record.get("dest_list_id")
                for record in dest_list_records
                if record.get("dest_list_id")
            ]
            self._logger.info(
                f"AlertActionsAPI: Found {len(dest_list_ids)} destination lists for org_id={org_id}"
            )

            # Get block_destinations alert actions by destination_list_id
            for dest_list_id in dest_list_ids:
                dest_saved_searches = manager.get_saved_searches_with_alert_actions(
                    destination_list_id=dest_list_id
                )
                for ss in dest_saved_searches:
                    if ss.name not in seen_names:
                        all_saved_searches.append(ss)
                        seen_names.add(ss.name)
                self._logger.info(
                    f"AlertActionsAPI: Found {len(dest_saved_searches)} block_destinations alert actions for dest_list_id={dest_list_id}"
                )

            if not all_saved_searches:
                self._logger.info(
                    f"AlertActionsAPI: No alert actions found for org_id={org_id}"
                )
                return {
                    "payload": {
                        "deleted_count": 0,
                        "message": f"No alert actions found for organization {org_id}",
                    },
                    "status": 200,
                }

            # Log names
            for ss in all_saved_searches:
                self._logger.info(
                    f"AlertActionsAPI: Deleting saved search: {ss.name} (org_id={org_id})"
                )

            manager.delete_saved_searches(all_saved_searches)

            self._logger.info(
                f"AlertActionsAPI: Successfully deleted {len(all_saved_searches)} alert actions for org_id={org_id}"
            )

            return {
                "payload": {
                    "deleted_count": len(all_saved_searches),
                    "message": f"Successfully deleted {len(all_saved_searches)} alert action(s) for organization {org_id}",
                },
                "status": 200,
            }

        except Exception as e:
            self._logger.error(
                f"AlertActionsAPI: Error deleting alert actions for org_id={org_id}: {str(e)}"
            )
            return {
                "payload": {"message": f"Failed to delete alert actions: {str(e)}"},
                "status": 500,
            }
