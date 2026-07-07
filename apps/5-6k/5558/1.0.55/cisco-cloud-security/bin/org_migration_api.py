# encoding = utf-8
"""REST API handler for triggering organization data migration."""

from __future__ import print_function

import sys
from os.path import dirname, abspath
from typing import Any, Dict

sys.path.append(dirname(abspath(__file__)))

import json
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from logger import Logger
from common import Common

from exceptions import (
    NewInstallationException,
    MigrationFailedException,
)
from org_migration_manager import OrgMigrationManager

kv_service = None


class OrgMigrationAPI(PersistentServerConnectionApplication):
    """
    REST API handler for triggering organization data migration.

    This class provides an endpoint for manually triggering the migration
    of legacy data to include organization IDs. It is used during upgrades
    from older versions of the app.

    The handler supports the following HTTP methods:
        - POST: Trigger organization data migration.

    Example:
        The handler is invoked via Splunk's REST API:
        ```
        POST /servicesNS/nobody/cisco-cloud-security/org_migration
        ```
    """

    def __init__(self, command_line, command_arg):
        """
        Initialize the OrgMigrationAPI REST API handler.

        Sets up the handler with default values for session management,
        KV store service, and logging.

        Args:
            command_line (str): The command line string passed by Splunk.
            command_arg (str): Additional command arguments passed by Splunk.
        """
        PersistentServerConnectionApplication.__init__(self)
        self._session_token = None
        self._kv_service = None
        self._logger = Logger()

    def handle(self, in_string):
        """
        Handle incoming REST API requests and route to appropriate methods.

        Parses the incoming request, initializes required services, and routes
        the request to the migration trigger handler.

        Args:
            in_string (str): JSON-encoded string containing the request parameters,
                including session information, HTTP method, and payload.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Response data or error message.
                - status (int): HTTP status code.
        """
        self._logger.info("OrgMigrationAPI.handle() called - starting request processing")
        try:
            self._logger.info("OrgMigrationAPI: Parsing input string")
            params = Common().parse_in_string(in_string)
            self._session_token = params["session"]["authtoken"]
            self._logger.info("OrgMigrationAPI: Session token obtained, initializing KV service")
            self._init_kv_service()
            method: str = params["method"]
            self._logger.info(f"OrgMigrationAPI: method={method}")

            if method.lower() == "post":
                self._logger.info("OrgMigrationAPI: Routing to trigger_migration()")
                return self.trigger_migration()
            else:
                self._logger.info(f"OrgMigrationAPI: Method {method} not supported")
                return {"payload": {"message": "Method not supported"}, "status": 405}

        except Exception as e:
            self._logger.error("API: org_migration_api, Exception : {0}".format(str(e)))
            return {"payload": {"message": str(e)}, "status": 500}

    def trigger_migration(self) -> Dict[str, Any]:
        """
        Trigger migration of all collections to include orgId.

        Initiates the organization migration process to update legacy records
        with organization IDs. This is useful for upgrading from older versions
        of the app or recovering from partial migrations.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Contains 'message', 'success' flag, and migration
                    statistics (migrated, skipped, failed counts, errors array)
                    on success, or error message on failure.
                - status (int): HTTP status code (200 for success, 500 for errors).
        """
        self._logger.info("OrgMigrationAPI.trigger_migration() - starting migration")
        try:
            self._logger.info("OrgMigrationAPI: Creating OrgMigrationManager")
            migration_mgr = OrgMigrationManager(
                session_token=self._session_token,
                kv_service=self._kv_service,
            )
            self._logger.info("OrgMigrationAPI: Calling perform_migration()")
            result = migration_mgr.perform_migration()
            self._logger.info(
                f"OrgMigrationAPI: Migration completed - migrated={result.total_migrated}, "
                f"skipped={result.total_skipped}, failed={result.total_failed}"
            )
            return {
                "payload": {
                    "message": "Migration completed successfully.",
                    "success": result.success,
                    "migrated": result.total_migrated,
                    "skipped": result.total_skipped,
                    "failed": result.total_failed,
                    "errors": result.errors,
                },
                "status": 200,
            }
        except NewInstallationException:
            self._logger.info("OrgMigrationAPI: NewInstallationException - no orgs configured")
            return {
                "payload": {
                    "message": "No organizations found. Please configure OAuth settings first.",
                    "success": True,
                    "migrated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "errors": [],
                },
                "status": 200,
            }
        except MigrationFailedException as e:
            self._logger.error(f"OrgMigrationAPI: MigrationFailedException - {e}")
            return {
                "payload": {
                    "message": "Migration failed. Unable to determine organization IDs.",
                    "success": False,
                    "migrated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "errors": [str(e)] if str(e) else ["Unable to determine organization IDs"],
                },
                "status": 500,
            }
        except Exception as e:
            self._logger.error(f"OrgMigrationAPI: Migration trigger failed with unexpected error: {e}")
            return {
                "payload": {
                    "message": f"Migration failed: {str(e)}",
                    "success": False,
                    "migrated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "errors": [str(e)],
                },
                "status": 500,
            }

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
