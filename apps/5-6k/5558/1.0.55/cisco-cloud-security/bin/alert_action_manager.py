# encoding = utf-8
"""Manager for handling alert action migrations for multi-org support."""

import sys
from os.path import dirname, abspath
from typing import List, Optional, Dict, Any

sys.path.append(dirname(abspath(__file__)))

import splunklib.client as client
from splunklib.binding import HTTPError
from logger import Logger
from enums import AlertActionType
from utils import str_to_boolean


class AlertActionManager:
    """
    Manager class for accessing and updating saved searches with alert actions.

    This manager handles migration of existing alert actions to include org_id
    for multi-organization support. It filters only saved searches that belong
    to the cisco-cloud-security app and have one of the app's custom alert actions enabled.
    """

    APP_NAME = "cisco-cloud-security"
    # Alert actions that require org_id migration
    MIGRATABLE_ACTIONS = [
        AlertActionType.INVESTIGATE_DESTINATIONS,
        AlertActionType.INVESTIGATE_REPORTS,
    ]
    # All alert actions defined by the app
    ALL_ALERT_ACTIONS = [
        AlertActionType.BLOCK_DESTINATIONS,
        AlertActionType.INVESTIGATE_DESTINATIONS,
        AlertActionType.INVESTIGATE_REPORTS,
    ]

    def __init__(self, session_key: str, host: str = "localhost", port: int = 8089):
        """
        Initializes the AlertActionManager.

        Args:
            session_key: The Splunk session key for authentication.
            host: The Splunk management host. Defaults to "localhost".
            port: The Splunk management port. Defaults to 8089.
        """
        self._logger = Logger()
        # Use owner="-" to access saved searches across all users
        # Use app=APP_NAME to filter only our app's saved searches
        self.service = client.connect(
            host=host,
            port=port,
            token=session_key,
            app=self.APP_NAME,
            owner="-",
        )

    def _get_saved_searches(self):
        """
        Returns the SavedSearches collection object.

        Returns:
            splunklib.client.SavedSearches: The saved searches collection object.
        """
        return self.service.saved_searches

    def _has_alert_action_enabled(
        self, saved_search, action_type: AlertActionType
    ) -> bool:
        """
        Check if a saved search has a specific alert action enabled.

        Args:
            saved_search: The splunklib saved search object.
            action_type: The alert action type to check.

        Returns:
            True if the alert action is enabled, False otherwise.
        """
        action_key = f"action.{action_type.value}"
        return str_to_boolean(saved_search.content.get(action_key, "0"))

    def _get_alert_action_param(
        self, saved_search, action_type: AlertActionType, param_name: str
    ) -> Optional[str]:
        """
        Get a parameter value from an alert action on a saved search.

        Args:
            saved_search: The splunklib saved search object.
            action_type: The alert action type.
            param_name: The parameter name to retrieve.

        Returns:
            The parameter value or None if not set.
        """
        param_key = f"action.{action_type.value}.param.{param_name}"
        return saved_search.content.get(param_key)

    def get_alert_action_org_id(
        self, saved_search, action_type: AlertActionType
    ) -> Optional[str]:
        """
        Get the org_id configured for an alert action on a saved search.

        Args:
            saved_search: The splunklib saved search object.
            action_type: The alert action type.

        Returns:
            The org_id value or None if not set.
        """
        return self._get_alert_action_param(saved_search, action_type, "org_id")

    def get_block_destinations_list_id(self, saved_search) -> Optional[str]:
        """
        Get the destination_list_id configured for block_destinations alert action.

        Args:
            saved_search: The splunklib saved search object.

        Returns:
            The destination_list_id value or None if not set.
        """
        return self._get_alert_action_param(
            saved_search, AlertActionType.BLOCK_DESTINATIONS, "destination_list_id"
        )

    def _matches_alert_action_filter(
        self,
        saved_search,
        org_id: Optional[str] = None,
        destination_list_id: Optional[str] = None,
    ) -> bool:
        """
        Check if a saved search matches the alert action filter criteria.

        Args:
            saved_search: The splunklib saved search object.
            org_id: Optional organization ID to filter by (for investigate_destinations
                and investigate_reports actions).
            destination_list_id: Optional destination list ID to filter by
                (for block_destinations action).

        Returns:
            True if the saved search has at least one alert action enabled
            and matches the filter criteria (if provided). If both filters are
            provided, returns True if either condition is met.
        """
        no_filters = org_id is None and destination_list_id is None

        for action_type in self.ALL_ALERT_ACTIONS:
            if not self._has_alert_action_enabled(saved_search, action_type):
                continue

            # No filters - return True if any action is enabled
            if no_filters:
                return True

            # Check block_destinations for destination_list_id match
            if (
                destination_list_id is not None
                and action_type == AlertActionType.BLOCK_DESTINATIONS
            ):
                if self.get_block_destinations_list_id(saved_search) == destination_list_id:
                    return True

            # Check other actions for org_id match
            if org_id is not None and action_type != AlertActionType.BLOCK_DESTINATIONS:
                if self.get_alert_action_org_id(saved_search, action_type) == org_id:
                    return True

        return False

    def get_saved_searches_with_alert_actions(
        self,
        org_id: Optional[str] = None,
        destination_list_id: Optional[str] = None,
    ) -> List[Any]:
        """
        Get all saved searches that have any of the app's alert actions enabled.

        Args:
            org_id: Optional organization ID to filter by. If provided, only returns
                saved searches where investigate_destinations or investigate_reports
                actions have this org_id configured.
            destination_list_id: Optional destination list ID to filter by. If provided,
                only returns saved searches where block_destinations action has this
                destination_list_id configured.

        Returns:
            List of saved search objects that have at least one of the app's
            alert actions enabled and match the filter criteria (if provided).
            If both filters are provided, returns searches matching either condition.
        """
        try:
            saved_searches = self._get_saved_searches()
            matching_searches = [
                s
                for s in saved_searches
                if self._matches_alert_action_filter(s, org_id, destination_list_id)
            ]
            filter_msg = ""
            if org_id:
                filter_msg += f" for org_id {org_id}"
            if destination_list_id:
                filter_msg += f" for destination_list_id {destination_list_id}"
            self._logger.info(
                f"Found {len(matching_searches)} saved searches with app alert actions"
                + (filter_msg + "." if filter_msg else ".")
            )
            return matching_searches
        except Exception as e:
            self._logger.error(f"Error retrieving saved searches: {e}")
            raise

    def update_alert_action_org_id(
        self, saved_search, action_type: AlertActionType, org_id: str
    ) -> bool:
        """
        Update the org_id parameter for an alert action on a saved search.

        Args:
            saved_search: The splunklib saved search object.
            action_type: The alert action type to update.
            org_id: The organization ID to set.

        Returns:
            True if update was successful, False otherwise.
        """
        try:
            param_key = f"action.{action_type.value}.param.org_id"
            saved_search.update(**{param_key: org_id})
            self._logger.info(
                f"Updated {saved_search.name} action {action_type.value} with org_id {org_id}"
            )
            return True
        except HTTPError as e:
            self._logger.error(
                f"HTTP error updating saved search {saved_search.name}: {e}"
            )
            return False
        except Exception as e:
            self._logger.error(f"Error updating saved search {saved_search.name}: {e}")
            return False

    def migrate_alert_actions(self, org_id: str) -> Dict[str, Any]:
        """
        Migrate all eligible alert actions to include org_id.

        This method:
        1. Finds all saved searches with the app's alert actions enabled
        2. For each migratable action (investigate_destinations, investigate_reports):
           - Skips if org_id is already set
           - Updates with the provided org_id

        Note: block_destinations is not migrated as it derives org_id from
        the destination list's KVStore record.

        Args:
            org_id: The organization ID to set on alert actions.

        Returns:
            Dictionary with migration statistics:
            - total_searches: Number of saved searches found with alert actions
            - migrated: Number of alert actions successfully migrated
            - skipped: Number of alert actions skipped (already have org_id)
            - failed: Number of alert actions that failed to migrate
        """
        stats = {"total_searches": 0, "migrated": 0, "skipped": 0, "failed": 0}

        try:
            saved_searches = self.get_saved_searches_with_alert_actions()
            stats["total_searches"] = len(saved_searches)

            for saved_search in saved_searches:
                for action_type in self.MIGRATABLE_ACTIONS:
                    if not self._has_alert_action_enabled(saved_search, action_type):
                        continue

                    # Check if org_id is already set
                    existing_org_id = self.get_alert_action_org_id(
                        saved_search, action_type
                    )
                    if existing_org_id:
                        self._logger.info(
                            f"Skipping {saved_search.name} action {action_type.value} - "
                            f"org_id already set to {existing_org_id}"
                        )
                        stats["skipped"] += 1
                        continue

                    # Update with org_id
                    if self.update_alert_action_org_id(
                        saved_search, action_type, org_id
                    ):
                        stats["migrated"] += 1
                    else:
                        stats["failed"] += 1

            self._logger.info(
                f"Alert action migration completed. "
                f"Total searches: {stats['total_searches']}, "
                f"Migrated: {stats['migrated']}, "
                f"Skipped: {stats['skipped']}, "
                f"Failed: {stats['failed']}"
            )

        except Exception as e:
            self._logger.error(f"Alert action migration failed: {e}")
            raise

        return stats

    def delete_saved_searches(self, saved_searches: List[Any]) -> None:
        """
        Delete a list of saved searches.

        Args:
            saved_searches: List of splunklib saved search objects to delete.

        Raises:
            HTTPError: If an HTTP error occurs during deletion.
            Exception: If any other error occurs during deletion.
        """
        for saved_search in saved_searches:
            name = saved_search.name
            try:
                saved_search.delete()
                self._logger.info(f"Deleted saved search: {name}")
            except HTTPError as e:
                self._logger.error(f"HTTP error deleting saved search {name}: {e}")
                raise
            except Exception as e:
                self._logger.error(f"Error deleting saved search {name}: {e}")
                raise

        self._logger.info(f"Successfully deleted {len(saved_searches)} saved searches.")
