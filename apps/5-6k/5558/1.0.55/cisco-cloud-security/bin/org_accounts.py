# encoding = utf-8
from __future__ import print_function

from datetime import timezone
import datetime
import sys
from os.path import dirname, abspath
from typing import Any, Dict, List, Optional

sys.path.append(dirname(abspath(__file__)))

import json
from validator import cummulative_validator, date_validator
from splunk.persistconn.application import PersistentServerConnectionApplication
from service.app_kvstore_service import KVStoreService
from enum import Enum
from logger import Logger
from common import Common
from enums import (
    KvStoreCollections,
    KvStoreFilterQueries,
    KvStorePaginatedRecords,
    KvStoreRecordsPagination,
    OAuthSettingsModificationStatus,
    OAuthSettingsStatus,
    ModularInputConfig,
    ModInputType,
    ModInputInterval,
)
from collections_schema import (
    AlertsIndexFields,
    AppDiscoveryIndexFields,
    InvestigateSettingsFields,
    OAuthSettingsFields,
    PrivateAppIndexFields,
    BaseCollectionFields,
)
from reporting_api_client import ReportingAPIClient
from exceptions import (
    ReportingAPIClientException,
    OrgAccountsException,
    ModularInputNotFoundException,
    KvStoreRecordNotFoundException,
)
from token_service import TokenService
from modular_input_manager import ModularInputManager
from utils import (
    format_response_for_data_table,
    mask_credentials,
    MASK_LENGTH,
    get_kvstore_pagination_params,
    paginate_kvstore_records,
)
from global_org_client import GlobalOrgClient

kv_service = None
REQUIRED_FIELDS = [
    "apiKey",
    "apiSecret",
    "baseURL",
    "orgId",
    "timezone",
    "storageRegion",
]
CREDENTIAL_FIELDS = ["apiKey", "apiSecret", "baseURL"]


class GetOrgAccountsFields(Enum):
    """
    Enum defining the field categories for retrieving org account data.

    This enum specifies which sets of fields should be included when fetching
    organization account information. It controls the granularity of data
    returned by the _get_accounts and _populate_account_data methods.

    Attributes:
        ALL: Include all field categories (OAuth, investigate, privateapp, appdiscovery, alerts).
        OAUTH_FIELDS: Include only OAuth credential and configuration fields.
        INDEX_FIELDS: Include all index-related fields (investigate, privateapp, appdiscovery, alerts).
        INVESTIGATE_FIELDS: Include only investigate index settings.
        APPDISCOVERY_FIELDS: Include only app discovery index settings.
        PRIVATEAPP_FIELDS: Include only private app index settings.
        ALERTS_FIELDS: Include only alerts index settings.
    """

    ALL = "all"
    OAUTH_FIELDS = "oauth_fields"
    INDEX_FIELDS = "index_fields"
    INVESTIGATE_FIELDS = "investigate_fields"
    APPDISCOVERY_FIELDS = "appdiscovery_fields"
    PRIVATEAPP_FIELDS = "privateapp_fields"
    ALERTS_FIELDS = "alerts_fields"


class OrgAccounts(PersistentServerConnectionApplication):
    """
    REST API handler for managing organization accounts in the Cisco Cloud Security app.

    This class provides CRUD operations for organization accounts, including OAuth
    credentials, investigate settings, private app indexes, and app discovery indexes.
    It extends Splunk's PersistentServerConnectionApplication to handle REST API requests.

    The handler supports the following HTTP methods:
        - GET: Retrieve account(s) with optional field filtering and pagination.
        - POST: Create a new organization account or fetch org ID from credentials.
        - PUT: Update an existing organization account.
        - DELETE: Remove an organization account and all associated data.

    Attributes:
        OAUTH_COLLECTION (str): KV store collection name for OAuth settings.
        INVESTIGATE_COLLECTION (str): KV store collection name for investigate settings.
        PRIVATEAPP_INDEXES_COLLECTION (str): KV store collection name for private app indexes.
        APPDISCOVERY_INDEXES_COLLECTION (str): KV store collection name for app discovery indexes.

    Example:
        The handler is invoked via Splunk's REST API:
        ```
        GET /servicesNS/nobody/cisco-cloud-security/org_accounts?orgId=12345
        POST /servicesNS/nobody/cisco-cloud-security/org_accounts
        PUT /servicesNS/nobody/cisco-cloud-security/org_accounts?orgId=12345
        DELETE /servicesNS/nobody/cisco-cloud-security/org_accounts?orgId=12345
        ```
    """

    OAUTH_COLLECTION = KvStoreCollections.OAUTH_SETTINGS.value
    INVESTIGATE_COLLECTION = KvStoreCollections.INVESTIGATE_SETTINGS.value
    PRIVATEAPP_INDEXES_COLLECTION = KvStoreCollections.PRIVATEAPP_INDEXES.value
    APPDISCOVERY_INDEXES_COLLECTION = KvStoreCollections.APPDISCOVERY_INDEXES.value
    ALERTS_INDEXES_COLLECTION = KvStoreCollections.ALERTS_INDEXES.value

    def __init__(self, command_line, command_arg):
        """
        Initialize the OrgAccounts REST API handler.

        Sets up the handler with default values for session management,
        KV store service, modular input manager, and logging.

        Args:
            command_line (str): The command line string passed by Splunk.
            command_arg (str): Additional command arguments passed by Splunk.
        """
        PersistentServerConnectionApplication.__init__(self)
        self._session_token = None
        self._kv_service = None
        self._mod_inputs_mgr = None
        self._global_org_client = None
        self._user = None
        self._logger = Logger()

    def _validator(self, arg: Any, method: str, name: str) -> Any:
        """
        Validate a field value using the specified validation method.

        Applies either cumulative validation or date validation to the provided
        argument based on the method parameter.

        Args:
            arg (Any): The value to validate.
            method (str): Validation method identifier. Use 'cu' for cumulative
                validator or 'da' for date validator.
            name (str): Field name used in error messages for identification.

        Returns:
            Any: The validated argument if validation passes.

        Raises:
            OrgAccountsException: If validation fails for the specified field.
        """
        if method == "cu":
            if not cummulative_validator(str(arg)):
                raise OrgAccountsException(f"Validation failed for field [{name}]")
            return arg
        elif method == "da":
            if not date_validator(str(arg)):
                raise OrgAccountsException(f"Validation failed for date field [{name}]")
            return arg
        return arg

    def handle(self, in_string):
        """
        Handle incoming REST API requests and route to appropriate methods.

        Parses the incoming request, initializes required services, and routes
        the request to the appropriate handler method based on the HTTP method.

        Args:
            in_string (str): JSON-encoded string containing the request parameters,
                including session information, HTTP method, query parameters,
                and payload.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Response data or error message.
                - status (int): HTTP status code.
        """
        try:
            params = Common().parse_in_string(in_string)
            self._session_token = params["session"]["authtoken"]
            self._user = params["session"]["user"]
            self._init_kv_service()
            self._init_mod_inputs_mgr()
            self._global_org_client = GlobalOrgClient(self._session_token)
            method: str = params["method"]
            query_params = params.get("query", {})
            payload = json.loads(params.get("payload", "{}"))
            if method.lower() == "get":
                return self._get_accounts(query_params)
            elif method.lower() == "post":
                action = query_params.get("action", "")
                if action == "get_orgId":
                    return self._get_org_id_from_credentials(payload)
                return self._create_account(payload)
            elif method.lower() == "put":
                return self._update_account(query_params, payload)
            elif method.lower() == "delete":
                return self._delete_account(query_params)
            else:
                return {"payload": {"message": "Method not supported"}, "status": 405}

        except Exception as e:
            self._logger.error("API: org_accounts, Exception : {0}".format(str(e)))
            return {"payload": {"message": str(e)}, "status": 500}

    def _get_accounts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve organization account(s) based on query parameters.

        Fetches either a single account by orgId or a paginated list of all accounts.
        Supports filtering by field categories to control which data is returned.

        Args:
            params (Dict[str, Any]): Query parameters containing:
                - orgId (str, optional): Specific organization ID to retrieve.
                - fields (str, optional): Field category filter. Defaults to 'oauth_fields'.
                    Valid values: 'all', 'oauth_fields', 'index_fields',
                    'investigate_fields', 'appdiscovery_fields', 'privateapp_fields'.
                - draw (int, optional): DataTables draw counter for pagination.
                - start (int, optional): Pagination offset.
                - length (int, optional): Number of records per page.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Account data or paginated list with metadata.
                - status (int): HTTP status code (200 for success, 400/404 for errors).
        """
        org_id = params.get("orgId", "")
        fields_param = params.get("fields", "oauth_fields")
        try:
            field = GetOrgAccountsFields(fields_param)
        except ValueError:
            return {
                "payload": {
                    "message": "Invalid fields parameter. Supported values are 'all', 'oauth_fields', 'index_fields', 'investigate_fields', 'appdiscovery_fields', 'privateapp_fields'"
                },
                "status": 400,
            }

        if org_id:
            account_data = self._populate_account_data(org_id, field)
            if not account_data:
                return {
                    "payload": {"message": f"Account not found for orgId: {org_id}"},
                    "status": 404,
                }
            # Wrap single account in same format as list response for consistency
            paginated_result = KvStorePaginatedRecords(
                total_records=1, records=[account_data]
            )
            return {
                "payload": format_response_for_data_table(
                    paginated_result, draw=params.get("draw", 1)
                ),
                "status": 200,
            }

        if field not in (GetOrgAccountsFields.ALL, GetOrgAccountsFields.OAUTH_FIELDS):
            return {
                "payload": {
                    "message": "Only 'all' or 'oauth_fields' are supported for list operation"
                },
                "status": 400,
            }

        paginated_records = self._get_all_oauth_records(
            get_kvstore_pagination_params(params)
        )

        for record in paginated_records.records:
            account_data = self._populate_account_data(
                record.get("orgId", ""), field, oauth_record=record
            )
            record.update(account_data)

        return {
            "payload": format_response_for_data_table(
                paginated_records, draw=params.get("draw", 1)
            ),
            "status": 200,
        }

    def _populate_account_data(
        self,
        org_id: str,
        field: GetOrgAccountsFields,
        oauth_record: Any = None,
    ) -> Dict[str, Any]:
        """
        Build account data dictionary based on requested field categories.

        Assembles account information by fetching data from various KV store
        collections based on the specified field filter. Masks sensitive
        credential data before returning.

        Args:
            org_id (str): The organization ID to fetch data for.
            field (GetOrgAccountsFields): Field category enum specifying which
                data sets to include in the response.
            oauth_record (Any, optional): Pre-fetched OAuth record to avoid
                redundant KV store queries. Defaults to None.

        Returns:
            Dict[str, Any]: Dictionary containing the requested account data fields.
                May include OAuth settings, investigate_index, privateapp_index,
                and/or appdiscovery_index based on the field parameter.
        """
        account_data = {}

        def should_include(target_field):
            if field == GetOrgAccountsFields.ALL:
                return True
            if field == GetOrgAccountsFields.INDEX_FIELDS:
                return target_field in (
                    GetOrgAccountsFields.INVESTIGATE_FIELDS,
                    GetOrgAccountsFields.PRIVATEAPP_FIELDS,
                    GetOrgAccountsFields.APPDISCOVERY_FIELDS,
                    GetOrgAccountsFields.ALERTS_FIELDS,
                )
            return field == target_field

        if should_include(GetOrgAccountsFields.OAUTH_FIELDS):
            if oauth_record is None:
                oauth_record = self._get_oauth_record(org_id)
            if oauth_record:
                records_to_mask = (
                    oauth_record if isinstance(oauth_record, list) else [oauth_record]
                )
                account_data.update(mask_credentials(records_to_mask)[0])
            else:
                return {}
        else:
            oauth_record = self._get_oauth_record(org_id)
            if not oauth_record:
                return {}
            account_data.update({field.value: None for field in OAuthSettingsFields})
        if should_include(GetOrgAccountsFields.INVESTIGATE_FIELDS):
            investigate_record = self._get_investigate_record(org_id)
            account_data["investigate_index"] = (
                investigate_record.get("index", "") if investigate_record else ""
            )
        else:
            account_data["investigate_index"] = None
        if should_include(GetOrgAccountsFields.PRIVATEAPP_FIELDS):
            account_data["privateapp_index"] = self._get_privateapp_index(org_id)
        else:
            account_data["privateapp_index"] = None
        if should_include(GetOrgAccountsFields.APPDISCOVERY_FIELDS):
            account_data["appdiscovery_index"] = self._get_appdiscovery_index(org_id)
        else:
            account_data["appdiscovery_index"] = None
        if should_include(GetOrgAccountsFields.ALERTS_FIELDS):
            account_data["alerts_index"] = self._get_alerts_index(org_id)
        else:
            account_data["alerts_index"] = None

        return account_data

    def _create_account(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new organization account with associated settings and indexes.

        Creates OAuth credentials record and optionally sets up investigate settings,
        private app index, and app discovery index. Also creates corresponding
        modular inputs for data collection.

        Args:
            payload (Dict[str, Any]): Account creation data containing:
                - apiKey (str): API key for authentication.
                - apiSecret (str): API secret for authentication.
                - baseURL (str): Base URL for API endpoints.
                - orgId (str): Organization identifier.
                - timezone (str): Timezone for the organization.
                - storageRegion (str): Data storage region.
                - investigate_index (str, optional): Splunk index for investigate data.
                - privateapp_index (str, optional): Splunk index for private app data.
                - appdiscovery_index (str, optional): Splunk index for app discovery data.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Success message with orgId or error message.
                - status (int): HTTP status code (201 for created, 400/409/500 for errors).

        Raises:
            OrgAccountsException: If credential validation fails.
            ReportingAPIClientException: If API communication fails.
        """
        is_first_account: bool = False
        self._logger.info(f"Creating org account with payload: {payload}")
        # Frontend sends payload inside data key
        payload = payload.get("data", payload)
        try:
            if not self._validate_payload(payload, require_all_fields=True):
                return {
                    "payload": {"message": "Missing required fields in payload"},
                    "status": 400,
                }
        except OrgAccountsException as e:
            return {
                "payload": {"message": str(e)},
                "status": 400,
            }
        oauth_data = self._parse_payload_to_oauth_dict(payload)
        org_id = oauth_data.get("orgId")
        self._logger.info(f"Checking if account with orgId {org_id} already exists")
        if self._get_oauth_record(org_id):
            return {
                "payload": {"message": "Account with this orgId already exists"},
                "status": 409,
            }
        self._logger.info(
            f"Fetching account to know whether the new account is first account for the app"
        )
        if (
            self._get_all_oauth_records(
                KvStoreRecordsPagination(limit=1, skip=0)
            ).total_records
            == 0
        ):
            self._logger.info(f"{org_id} is the first account being created")
            is_first_account = True
        self._logger.info(f"Validating credentials for orgId {org_id}")
        try:
            self._logger.info(f"Creating OAuth record for orgId {org_id}")
            self._create_oauth_record(oauth_data, is_first_account)
        except (OrgAccountsException, ReportingAPIClientException) as e:
            return {
                "payload": {"message": f"Credential validation failed: {str(e)}"},
                "status": 400,
            }
        except Exception as e:
            return {
                "payload": {"message": f"Unexpected error: {str(e)}"},
                "status": 500,
            }
        if investigate_index := payload.get("investigate_index"):
            self._logger.info(
                f"Creating Investigate record for orgId {org_id}. Index: {investigate_index}"
            )
            investigate_data = self._parse_payload_to_investigate_dict(payload)
            self._insert_investigate_record(investigate_data)

        if privateapp_index := payload.get("privateapp_index"):
            self._logger.info(
                f"Creating PrivateApp record for orgId {org_id}. Index: {privateapp_index}"
            )
            self._insert_privateapp_record(org_id, privateapp_index)
            self._create_mod_input(ModInputType.PRIVATE_APPS, org_id, privateapp_index)

        if appdiscovery_index := payload.get("appdiscovery_index"):
            self._logger.info(
                f"Creating AppDiscovery record for orgId {org_id}. Index: {appdiscovery_index}"
            )
            self._insert_appdiscovery_record(org_id, appdiscovery_index)
            self._create_mod_input(
                ModInputType.APP_DISCOVERY, org_id, appdiscovery_index
            )

        if alerts_index := payload.get("alerts_index"):
            self._logger.info(
                f"Creating Alerts record for orgId {org_id}. Index: {alerts_index}"
            )
            self._insert_alerts_record(org_id, alerts_index)
            self._create_mod_input(ModInputType.ALERT_DASHBOARD_INDEX, org_id, alerts_index)

        self._logger.info(f"Account creation process completed for orgId {org_id}")
        return {
            "payload": {"message": "Account created successfully", "orgId": org_id},
            "status": 201,
        }

    def _create_oauth_record(
        self, oauth_data: Dict[str, Any], is_first_account: bool
    ) -> None:
        """
        Create an OAuth record in the KV store and store credentials securely.

        Validates the provided credentials, creates the OAuth record in the KV store,
        stores sensitive credentials in Splunk's secure password storage, and sets
        the global org if this is the first account.

        Args:
            oauth_data (Dict[str, Any]): OAuth configuration data containing apiKey,
                apiSecret, baseURL, orgId, timezone, and storageRegion.
            is_first_account (bool): Whether this is the first account being created
                for the app. If True, sets this org as the global org.

        Raises:
            OrgAccountsException: If credential validation fails or orgId mismatch.
            ReportingAPIClientException: If API communication fails during validation.
        """
        org_id = oauth_data.get("orgId")
        api_key = oauth_data.get("apiKey")
        api_secret = oauth_data.get("apiSecret")
        base_url = oauth_data.get("baseURL")
        access_token = self._validate_and_fetch_access_token(
            api_key,
            api_secret,
            base_url,
            org_id,
        )
        oauth_data.update(
            {
                "apiKey": "",
                "apiSecret": "",
                "configName": "dummy_value",
                "status": OAuthSettingsStatus.ACTIVE.value,
                "modificationStatus": OAuthSettingsModificationStatus.CREATED.value,
            }
        )

        self._kv_service.insert_record(
            self.OAUTH_COLLECTION, self._session_token, oauth_data
        )
        self._store_credentials(org_id, api_key, api_secret, access_token)
        if is_first_account:
            self._global_org_client.global_org = org_id

    def _validate_and_fetch_access_token(
        self, api_key: str, api_secret: str, base_url: str, org_id: str
    ):
        """
        Validate API credentials and fetch an access token.

        Creates a ReportingAPIClient to validate the provided credentials and
        retrieve an access token. Also verifies that the provided orgId matches
        the one associated with the credentials.

        Args:
            api_key (str): The API key for authentication.
            api_secret (str): The API secret for authentication.
            base_url (str): The base URL for API endpoints.
            org_id (str): The expected organization ID to validate against.

        Returns:
            str: The access token obtained from successful authentication.

        Raises:
            OrgAccountsException: If credentials are invalid or orgId doesn't match.
        """
        client = ReportingAPIClient(
            self._session_token,
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url,
            set_token=False,
        )
        if not client.org_id:
            raise OrgAccountsException(
                "Unable to fetch orgId with provided credentials"
            )
        if org_id and str(org_id) != str(client.org_id):
            raise OrgAccountsException("Provided orgId does not match with credentials")
        return client.token

    def _get_org_id_from_credentials(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch organization ID using provided API credentials without creating an account.

        Validates the provided API credentials by attempting to authenticate with
        the Reporting API and retrieves the associated organization ID.

        Args:
            payload (Dict[str, Any]): Credentials payload containing:
                - apiKey (str): API key for authentication.
                - apiSecret (str): API secret for authentication.
                - baseURL (str): Base URL for API endpoints.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Contains 'orgId' on success or error 'message'.
                - status (int): HTTP status code (200 for success, 400 for errors).
        """
        api_key = payload.get("apiKey")
        api_secret = payload.get("apiSecret")
        base_url = payload.get("baseURL")

        if not all([api_key, api_secret, base_url]):
            return {
                "payload": {"message": "apiKey, apiSecret, and baseURL are required"},
                "status": 400,
            }

        try:
            client = ReportingAPIClient(
                self._session_token,
                api_key=api_key,
                api_secret=api_secret,
                base_url=base_url,
                set_token=False,
            )
            if not client.org_id:
                return {
                    "payload": {
                        "message": "Failed to fetch Organization ID. Please check your credentials."
                    },
                    "status": 400,
                }
            return {"payload": {"orgId": client.org_id}, "status": 200}
        except (ReportingAPIClientException, OrgAccountsException) as e:
            self._logger.error(f"API: org_accounts, get_orgId action failed: {str(e)}")
            return {
                "payload": {
                    "message": "Failed to fetch Organization ID. Please check your credentials."
                },
                "status": 400,
            }

    def _validate_payload(
        self, payload: Dict[str, Any], require_all_fields: bool = True
    ) -> bool:
        """
        Validate payload fields for account creation or update operations.

        Performs validation on all fields present in the payload using appropriate
        validators. Can enforce that all required fields are present (for create)
        or only validate fields that are provided (for update).

        Args:
            payload (Dict[str, Any]): The payload data to validate containing
                account configuration fields.
            require_all_fields (bool, optional): If True, enforces that all
                REQUIRED_FIELDS must be present (used for create operations).
                If False, only validates fields that are present (used for
                update operations). Defaults to True.

        Returns:
            bool: True if validation passes. False if required fields are missing
                when require_all_fields is True.

        Raises:
            OrgAccountsException: If any field value fails validation checks.
        """
        if require_all_fields:
            if not self._is_oauth_fields_present(payload):
                return False

        for field in REQUIRED_FIELDS:
            if field in payload and payload[field]:
                self._validator(payload[field], "cu", field)

        if payload.get("investigate_index"):
            self._validator(payload["investigate_index"], "cu", "investigate_index")
        if payload.get("privateapp_index"):
            self._validator(payload["privateapp_index"], "cu", "privateapp_index")
        if payload.get("appdiscovery_index"):
            self._validator(payload["appdiscovery_index"], "cu", "appdiscovery_index")
        if payload.get("alerts_index"):
            self._validator(payload["alerts_index"], "cu", "alerts_index")
        if payload.get("userName"):
            self._validator(payload["userName"], "cu", "userName")
        if payload.get("createdDate"):
            self._validator(payload["createdDate"], "da", "createdDate")
        return True

    def _is_oauth_fields_present(
        self, payload: Dict[str, Any], required_fields: bool = True
    ) -> bool:
        """
        Check if OAuth fields are present in the payload.

        Verifies the presence of OAuth-related fields in the payload. Can check
        for all required fields or just any OAuth field presence.

        Args:
            payload (Dict[str, Any]): The payload to check for OAuth fields.
            required_fields (bool, optional): If True, checks that ALL required
                OAuth fields are present and non-empty. If False, checks if ANY
                OAuth field is present. Defaults to True.

        Returns:
            bool: When required_fields is True, returns True only if all required
                fields are present and non-empty. When required_fields is False,
                returns True if any OAuth field is present.
        """
        if required_fields:
            for field in REQUIRED_FIELDS:
                if field not in payload or not payload[field]:
                    return False
            return True
        return any(field in payload for field in REQUIRED_FIELDS)

    def _update_account(
        self, query_params: Dict[str, Any], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing organization account with new settings.

        Updates OAuth credentials, investigate settings, private app index,
        and/or app discovery index based on the provided payload. Creates
        new records if they don't exist for index settings.

        Args:
            query_params (Dict[str, Any]): Query parameters containing:
                - orgId (str): The organization ID of the account to update.
            payload (Dict[str, Any]): Update data containing any combination of:
                - apiKey (str, optional): New API key (requires all credential fields).
                - apiSecret (str, optional): New API secret (requires all credential fields).
                - baseURL (str, optional): New base URL (requires all credential fields).
                - timezone (str, optional): New timezone setting.
                - storageRegion (str, optional): New storage region.
                - investigate_index (str, optional): New investigate index.
                - privateapp_index (str, optional): New private app index.
                - appdiscovery_index (str, optional): New app discovery index.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Success message with orgId or error message.
                - status (int): HTTP status code (200 for success, 400/404/500 for errors).

        Raises:
            OrgAccountsException: If credential validation fails.
            ReportingAPIClientException: If API communication fails.
        """
        org_id = query_params.get("orgId")

        if not org_id:
            return {
                "payload": {"message": "orgId is required for update"},
                "status": 400,
            }

        oauth_record = self._get_oauth_record(org_id)
        if not oauth_record:
            return {"payload": {"message": "Account not found"}, "status": 404}

        has_oauth_fields = self._is_oauth_fields_present(payload, required_fields=False)

        if not payload.get("orgId"):
            payload["orgId"] = org_id

        # Validate all payload fields upfront
        try:
            self._validate_payload(payload, require_all_fields=False)
        except OrgAccountsException as e:
            return {
                "payload": {"message": str(e)},
                "status": 400,
            }

        if has_oauth_fields:
            oauth_data = self._parse_payload_to_oauth_dict(payload, is_update=True)
            try:
                self._logger.info(f"Updating OAuth record for orgId {org_id}")
                self._update_oauth_fields(oauth_data, oauth_record)
            except (OrgAccountsException, ReportingAPIClientException) as e:
                return {
                    "payload": {"message": f"Credential validation failed: {str(e)}"},
                    "status": 400,
                }
            except Exception as e:
                return {
                    "payload": {"message": f"Unexpected error: {str(e)}"},
                    "status": 500,
                }
            self._logger.info(f"OAuth record updated for orgId {org_id}")

        if "investigate_index" in payload:
            try:
                self._update_index_record(
                    self.INVESTIGATE_COLLECTION,
                    InvestigateSettingsFields.ORG_ID,
                    org_id,
                    payload["investigate_index"],
                )
            except KvStoreRecordNotFoundException:
                investigate_data = self._parse_payload_to_investigate_dict(payload)
                self._insert_investigate_record(investigate_data)

        if "privateapp_index" in payload:
            try:
                self._update_index_record(
                    self.PRIVATEAPP_INDEXES_COLLECTION,
                    PrivateAppIndexFields.ORG_ID,
                    org_id,
                    payload["privateapp_index"],
                )
                self._update_mod_input(
                    ModInputType.PRIVATE_APPS, org_id, payload["privateapp_index"]
                )
            except KvStoreRecordNotFoundException:
                self._insert_privateapp_record(org_id, payload["privateapp_index"])
                self._create_mod_input(
                    ModInputType.PRIVATE_APPS, org_id, payload["privateapp_index"]
                )
        if "appdiscovery_index" in payload:
            try:
                self._update_index_record(
                    self.APPDISCOVERY_INDEXES_COLLECTION,
                    AppDiscoveryIndexFields.ORG_ID,
                    org_id,
                    payload["appdiscovery_index"],
                )
                self._update_mod_input(
                    ModInputType.APP_DISCOVERY, org_id, payload["appdiscovery_index"]
                )
            except KvStoreRecordNotFoundException:
                self._insert_appdiscovery_record(org_id, payload["appdiscovery_index"])
                self._create_mod_input(
                    ModInputType.APP_DISCOVERY, org_id, payload["appdiscovery_index"]
                )
        if payload.get("alerts_index"):
            try:
                self._update_index_record(
                    self.ALERTS_INDEXES_COLLECTION,
                    AlertsIndexFields.ORG_ID,
                    org_id,
                    payload["alerts_index"],
                )
                self._update_mod_input(ModInputType.ALERT_DASHBOARD_INDEX, org_id, payload["alerts_index"])
            except KvStoreRecordNotFoundException:
                self._insert_alerts_record(org_id, payload["alerts_index"])
                self._create_mod_input(ModInputType.ALERT_DASHBOARD_INDEX, org_id, payload["alerts_index"])
        return {
            "payload": {"message": "Account updated successfully", "orgId": org_id},
            "status": 200,
        }

    def _update_oauth_fields(
        self, oauth_data: Dict[str, Any], oauth_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update OAuth credentials and settings for an organization.

        Updates the OAuth record with new credentials and/or settings. If credential
        fields are being updated, validates the new credentials before applying changes.
        Creates a new active record and marks the old one as inactive for audit purposes.

        Args:
            oauth_data (Dict[str, Any]): New OAuth data to apply. May include:
                - apiKey (str, optional): New API key.
                - apiSecret (str, optional): New API secret.
                - baseURL (str, optional): New base URL.
                - timezone (str, optional): New timezone.
                - storageRegion (str, optional): New storage region.
            oauth_record (Dict[str, Any]): Existing OAuth record from KV store
                including the '_key' field for identification.

        Returns:
            Dict[str, Any]: The updated OAuth record data.

        Raises:
            OrgAccountsException: If credential fields are partially provided
                (all three must be provided together) or validation fails.
        """
        access_token = None
        is_credential_update = any(field in oauth_data for field in CREDENTIAL_FIELDS)
        if is_credential_update and not all(
            field in oauth_data for field in CREDENTIAL_FIELDS
        ):
            raise OrgAccountsException(
                "apiKey, apiSecret, and baseURL must be provided together for update"
            )
        key = oauth_record.pop("_key")
        org_id = oauth_data.get("orgId")
        api_key = oauth_data.get("apiKey")
        api_secret = oauth_data.get("apiSecret")
        base_url = oauth_data.get("baseURL")
        if is_credential_update:
            api_key = (
                api_key
                if self._is_key_updated(api_key)
                else TokenService.get_token(
                    self._session_token, "api_key", org_id=org_id
                )
            )
            api_secret = (
                api_secret
                if self._is_key_updated(api_secret)
                else TokenService.get_token(
                    self._session_token, "api_secret", org_id=org_id
                )
            )
            access_token = self._validate_and_fetch_access_token(
                api_key,
                api_secret,
                base_url,
                org_id,
            )
        updated_record = {**oauth_record, **oauth_data}
        updated_record["apiKey"] = ""
        updated_record["apiSecret"] = ""
        updated_record["status"] = OAuthSettingsStatus.ACTIVE.value
        updated_record["modificationStatus"] = (
            OAuthSettingsModificationStatus.UPDATED.value
        )
        oauth_record["status"] = OAuthSettingsStatus.INACTIVE.value
        self._update_oauth_record(key, oauth_record)
        self._kv_service.insert_record(
            self.OAUTH_COLLECTION, self._session_token, updated_record
        )
        if is_credential_update:
            self._store_credentials(
                org_id,
                api_key,
                api_secret,
                access_token,
            )

    def _update_oauth_record(
        self, record_key: str, update_data: Dict[str, Any]
    ) -> None:
        """
        Update an OAuth record in the KV store by its key.

        Args:
            record_key (str): The unique key identifier of the record to update.
            update_data (Dict[str, Any]): The updated record data to save.
        """
        self._kv_service.update_item_by_key(
            self.OAUTH_COLLECTION, record_key, self._session_token, update_data
        )

    def _delete_account(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete an organization account and all associated data.

        Soft-deletes the OAuth record (marks as inactive), removes stored
        credentials, deletes associated modular inputs, and removes all
        index records (investigate, privateapp, appdiscovery).

        Args:
            params (Dict[str, Any]): Query parameters containing:
                - orgId (str): The organization ID of the account to delete.

        Returns:
            Dict[str, Any]: Response dictionary containing:
                - payload (Dict): Success or error message.
                - status (int): HTTP status code (200 for success, 400/404 for errors).

        Note:
            Deletion is restricted in two scenarios:
            - Cannot delete the last remaining account (app requires at least one).
            - Cannot delete the currently active global organization account.
        """
        org_id = params.get("orgId", "")

        if not org_id:
            return {
                "payload": {"message": "orgId is required for deletion"},
                "status": 400,
            }

        all_records = self._get_all_oauth_records(
            KvStoreRecordsPagination(limit=0, skip=0)
        )

        target_record = None
        for record in all_records.records:
            if record.get("orgId") == org_id:
                target_record = record
                break

        if not target_record:
            return {"payload": {"message": "Account not found"}, "status": 404}

        if all_records.total_records == 1:
            return {
                "payload": {
                    "message": "The app requires at least one organization account configured to function."
                },
                "status": 400,
            }

        if org_id == self._global_org_client.global_org:
            return {
                "payload": {"message": "Cannot delete an active account."},
                "status": 400,
            }
        self._delete_oauth_record(target_record)
        self._delete_credentials(org_id)
        self._delete_mod_inputs(org_id)
        self._delete_index_records(org_id)
        return {"payload": {"message": "Account deleted successfully"}, "status": 200}

    def _parse_payload_to_oauth_dict(
        self, payload: Dict[str, Any], is_update: bool = False
    ) -> Dict[str, Any]:
        """
        Extract OAuth-specific fields from the payload into a dictionary.

        Parses the input payload and extracts only the fields relevant to
        OAuth settings configuration.

        Args:
            payload (Dict[str, Any]): The raw payload containing account data.
            is_update (bool, optional): If True, excludes certain fields that
                should not be modified during updates (e.g., configName).
                Defaults to False.

        Returns:
            Dict[str, Any]: Dictionary containing only OAuth-related fields
                present in the payload.
        """
        parsed_data = {}
        for field in OAuthSettingsFields:
            if is_update and field in [
                OAuthSettingsFields.CONFIG_NAME,
            ]:
                continue
            if field.value in payload:
                parsed_data[field.value] = payload[field.value]
        return parsed_data

    def _parse_payload_to_investigate_dict(
        self, payload: Dict[str, Any], is_update: bool = False
    ) -> Dict[str, Any]:
        """
        Extract investigate settings fields from the payload into a dictionary.

        Parses the input payload and extracts fields relevant to investigate
        settings configuration. Maps 'investigate_index' to 'index' field.

        Args:
            payload (Dict[str, Any]): The raw payload containing account data.
            is_update (bool, optional): If True, excludes fields that should
                not be modified during updates (configName, userName, createdDate).
                Defaults to False.

        Returns:
            Dict[str, Any]: Dictionary containing investigate settings fields.
                Includes 'configName' and 'status' for new records.
        """
        parsed_data = {}
        for field in InvestigateSettingsFields:
            if is_update and field in [
                InvestigateSettingsFields.CONFIG_NAME,
                InvestigateSettingsFields.USER_NAME,
                InvestigateSettingsFields.CREATED_DATE,
            ]:
                continue
            if field.value in payload:
                parsed_data[field.value] = payload[field.value]
        if "investigate_index" in payload:
            parsed_data["index"] = payload["investigate_index"]
        if not is_update:
            parsed_data["configName"] = "dummy_value"
            parsed_data["status"] = OAuthSettingsStatus.ACTIVE.value
        return parsed_data

    def _get_all_oauth_records(
        self, pagination_details: KvStoreRecordsPagination
    ) -> KvStorePaginatedRecords:
        """
        Retrieve all active OAuth records with pagination support.

        Fetches active OAuth records from the KV store, applying sorting
        and pagination based on the provided parameters.

        Args:
            pagination_details (KvStoreRecordsPagination): Pagination configuration
                containing limit, skip, sort_by, and sort_direction parameters.

        Returns:
            KvStorePaginatedRecords: Paginated result containing the records
                and total count metadata.
        """
        query = KvStoreFilterQueries.ACTIVE_OAUTH_ORG_RECORD_QUERY
        records = json.loads(
            self._kv_service.query_items(
                self.OAUTH_COLLECTION,
                self._session_token,
                query_conditions=query,
                sort_by=pagination_details.sort_by,
                sort_direction=pagination_details.sort_direction,
            )
        )
        return paginate_kvstore_records(
            records, pagination_details.skip, pagination_details.limit
        )

    def _get_oauth_record(self, org_id: str) -> Dict[str, Any]:
        """
        Retrieve the active OAuth record for a specific organization.

        Queries the KV store for an active OAuth settings record matching
        the provided organization ID.

        Args:
            org_id (str): The organization ID to look up.

        Returns:
            Dict[str, Any]: The OAuth record if found, otherwise an empty dictionary.
        """
        query = {
            OAuthSettingsFields.ORG_ID.value: org_id,
            OAuthSettingsFields.STATUS.value: OAuthSettingsStatus.ACTIVE.value,
        }
        records = json.loads(
            self._kv_service.query_items(
                self.OAUTH_COLLECTION, self._session_token, query_conditions=query
            )
        )
        return records[0] if records else {}

    def _get_investigate_record(self, org_id: str) -> Dict[str, Any]:
        """
        Retrieve the investigate settings record for a specific organization.

        Queries the KV store for investigate settings matching the provided
        organization ID.

        Args:
            org_id (str): The organization ID to look up.

        Returns:
            Dict[str, Any]: The investigate settings record if found,
                otherwise an empty dictionary.
        """
        query = KvStoreFilterQueries.equals(InvestigateSettingsFields.ORG_ID, org_id)
        records = json.loads(
            self._kv_service.query_items(
                self.INVESTIGATE_COLLECTION, self._session_token, query_conditions=query
            )
        )
        return records[0] if records else {}

    def _insert_investigate_record(self, investigate_data: Dict[str, Any]) -> None:
        """
        Insert a new investigate settings record into the KV store.

        Args:
            investigate_data (Dict[str, Any]): The investigate settings data
                to insert, including orgId, index, and configuration fields.
        """
        self._kv_service.insert_record(
            self.INVESTIGATE_COLLECTION, self._session_token, investigate_data
        )

    def _get_privateapp_index(self, org_id: str) -> str:
        """
        Retrieve the private app index name for a specific organization.

        Queries the KV store for the private app index configuration
        matching the provided organization ID.

        Args:
            org_id (str): The organization ID to look up.

        Returns:
            str: The private app index name if found, otherwise an empty string.
        """
        query = KvStoreFilterQueries.equals(PrivateAppIndexFields.ORG_ID, org_id)
        records = json.loads(
            self._kv_service.query_items(
                self.PRIVATEAPP_INDEXES_COLLECTION,
                self._session_token,
                query_conditions=query,
            )
        )
        return records[0].get("index", "") if records else ""

    def _insert_privateapp_record(self, org_id: str, privateapp_index: str) -> None:
        """
        Insert a new private app index record into the KV store.

        Creates a record associating the organization with a Splunk index
        for storing private app data.

        Args:
            org_id (str): The organization ID.
            privateapp_index (str): The Splunk index name for private app data.
        """
        privateapp_data = {
            "orgId": org_id,
            "index": privateapp_index,
        }
        self._logger.info(f"Inserting PrivateApp record: {privateapp_data}")
        self._kv_service.insert_record(
            self.PRIVATEAPP_INDEXES_COLLECTION, self._session_token, privateapp_data
        )

    def _get_appdiscovery_index(self, org_id: str) -> str:
        """
        Retrieve the app discovery index name for a specific organization.

        Queries the KV store for the app discovery index configuration
        matching the provided organization ID.

        Args:
            org_id (str): The organization ID to look up.

        Returns:
            str: The app discovery index name if found, otherwise an empty string.
        """
        query = KvStoreFilterQueries.equals(AppDiscoveryIndexFields.ORG_ID, org_id)
        records = json.loads(
            self._kv_service.query_items(
                self.APPDISCOVERY_INDEXES_COLLECTION,
                self._session_token,
                query_conditions=query,
            )
        )
        return records[0].get("index", "") if records else ""

    def _insert_appdiscovery_record(self, org_id: str, appdiscovery_index: str) -> None:
        """
        Insert a new app discovery index record into the KV store.

        Creates a record associating the organization with a Splunk index
        for storing app discovery data.

        Args:
            org_id (str): The organization ID.
            appdiscovery_index (str): The Splunk index name for app discovery data.
        """
        appdiscovery_data = {
            "orgId": org_id,
            "index": appdiscovery_index,
        }
        self._logger.info(f"Inserting AppDiscovery record: {appdiscovery_data}")
        self._kv_service.insert_record(
            self.APPDISCOVERY_INDEXES_COLLECTION, self._session_token, appdiscovery_data
        )

    def _get_alerts_index(self, org_id: str) -> str:
        """
        Retrieve the alerts index name for a specific organization.

        Queries the KV store for the alerts index configuration
        matching the provided organization ID.

        Args:
            org_id (str): The organization ID to look up.

        Returns:
            str: The alerts index name if found, otherwise an empty string.
        """
        query = KvStoreFilterQueries.equals(AlertsIndexFields.ORG_ID, org_id)
        records = json.loads(
            self._kv_service.query_items(
                self.ALERTS_INDEXES_COLLECTION,
                self._session_token,
                query_conditions=query,
            )
        )
        return records[0].get("index", "") if records else ""

    def _insert_alerts_record(self, org_id: str, alerts_index: str) -> None:
        """
        Insert a new alerts index record into the KV store.

        Creates a record associating the organization with a Splunk index
        for storing alerts data.

        Args:
            org_id (str): The organization ID.
            alerts_index (str): The Splunk index name for alerts data.
        """
        alerts_data = {
            "orgId": org_id,
            "index": alerts_index,
        }
        self._logger.info(f"Inserting Alerts record: {alerts_data}")
        self._kv_service.insert_record(
            self.ALERTS_INDEXES_COLLECTION, self._session_token, alerts_data
        )

    def _update_index_record(
        self,
        collection: str,
        org_id_field: BaseCollectionFields,
        org_id: str,
        index: str,
    ) -> None:
        """
        Update an index record in the specified KV store collection.

        Finds the existing record by organization ID and updates the index
        field with the new value.

        Args:
            collection (str): The KV store collection name to update.
            org_id_field (BaseCollectionFields): The field enum representing
                the organization ID field in the collection.
            org_id (str): The organization ID to identify the record.
            index (str): The new index value to set.

        Raises:
            KvStoreRecordNotFoundException: If no record exists for the
                specified organization ID in the collection.
        """
        query = KvStoreFilterQueries.equals(org_id_field, org_id)
        records = json.loads(
            self._kv_service.query_items(
                collection,
                self._session_token,
                query_conditions=query,
            )
        )
        if not records:
            raise KvStoreRecordNotFoundException(
                f"Record not found in {collection} for orgId {org_id}"
            )
        key = records[-1].pop("_key")
        updated_record = {**records[-1], "index": index}
        self._kv_service.update_item_by_key(
            collection, key, self._session_token, updated_record
        )

    def _delete_oauth_record(self, record: Dict[str, Any]) -> None:
        """
        Soft-delete an OAuth record by marking it as inactive.

        Performs an audit-friendly deletion by marking the existing record
        as inactive and creating a new record with deletion metadata including
        the user who performed the deletion and timestamp.

        Args:
            record (Dict[str, Any]): The OAuth record to delete, including
                the '_key' field for identification.
        """
        record_key = record.pop("_key")
        record["status"] = OAuthSettingsStatus.INACTIVE.value
        deleted_record = {**record}
        deleted_record["modificationStatus"] = (
            OAuthSettingsModificationStatus.DELETED.value
        )
        deleted_record["userName"] = self._user
        deleted_record["createdDate"] = datetime.datetime.now(timezone.utc).strftime(
            "%Y/%m/%d %H:%M:%S"
        )
        self._kv_service.update_item_by_key(
            self.OAUTH_COLLECTION, record_key, self._session_token, record
        )
        self._kv_service.insert_record(
            self.OAUTH_COLLECTION, self._session_token, deleted_record
        )

    def _delete_investigate_record(self, org_id: str) -> None:
        """
        Delete the investigate settings record for a specific organization.

        Removes the investigate settings record from the KV store matching
        the provided organization ID.

        Args:
            org_id (str): The organization ID whose investigate record to delete.
        """
        self._kv_service.delete_items_by_condition(
            self.INVESTIGATE_COLLECTION,
            self._session_token,
            KvStoreFilterQueries.equals(InvestigateSettingsFields.ORG_ID, org_id),
        )

    def _delete_privateapp_record(self, org_id: str) -> None:
        """
        Delete the private app index record for a specific organization.

        Removes the private app index record from the KV store matching
        the provided organization ID.

        Args:
            org_id (str): The organization ID whose private app record to delete.
        """
        self._kv_service.delete_items_by_condition(
            self.PRIVATEAPP_INDEXES_COLLECTION,
            self._session_token,
            KvStoreFilterQueries.equals(PrivateAppIndexFields.ORG_ID, org_id),
        )

    def _delete_appdiscovery_record(self, org_id: str) -> None:
        """
        Delete the app discovery index record for a specific organization.

        Removes the app discovery index record from the KV store matching
        the provided organization ID.

        Args:
            org_id (str): The organization ID whose app discovery record to delete.
        """
        self._kv_service.delete_items_by_condition(
            self.APPDISCOVERY_INDEXES_COLLECTION,
            self._session_token,
            KvStoreFilterQueries.equals(AppDiscoveryIndexFields.ORG_ID, org_id),
        )

    def _delete_alerts_record(self, org_id: str) -> None:
        """
        Delete the alerts index record for a specific organization.

        Removes the alerts index record from the KV store matching
        the provided organization ID.

        Args:
            org_id (str): The organization ID whose alerts record to delete.
        """
        self._kv_service.delete_items_by_condition(
            self.ALERTS_INDEXES_COLLECTION,
            self._session_token,
            KvStoreFilterQueries.equals(AlertsIndexFields.ORG_ID, org_id),
        )

    def _delete_index_records(self, org_id: str) -> None:
        """
        Delete all index records for a specific organization.

        Removes investigate settings, private app index, app discovery
        index, and alerts index records associated with the organization.

        Args:
            org_id (str): The organization ID whose index records to delete.
        """
        self._delete_investigate_record(org_id)
        self._delete_privateapp_record(org_id)
        self._delete_appdiscovery_record(org_id)
        self._delete_alerts_record(org_id)

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

    def _is_key_updated(self, key: str) -> bool:
        """
        Check if a credential key has been updated from its masked value.

        Determines whether the provided key is a new value or still the
        masked placeholder used for displaying credentials.

        Args:
            key (str): The credential key value to check.

        Returns:
            bool: True if the key is a new value (not masked), False if
                it's still the masked placeholder.
        """
        return key != "*" * MASK_LENGTH

    def _init_mod_inputs_mgr(self):
        """
        Initialize the modular inputs manager.

        Creates a new ModularInputManager instance if one doesn't exist,
        enabling management of Splunk modular inputs for data collection.
        """
        if self._mod_inputs_mgr is None:
            self._mod_inputs_mgr = ModularInputManager(self._session_token)

    def _create_mod_input(self, type: ModInputType, org_id: str, index: str):
        """
        Create a new modular input for data collection.

        Creates a Splunk modular input configured to collect data for
        the specified type (private apps, app discovery, or alert dashboard) and organization.

        Args:
            type (ModInputType): The type of modular input to create.
            org_id (str): The organization ID to associate with the input.
            index (str): The Splunk index to store collected data.
        """
        config = ModularInputConfig(
            index=index,
            log_level="INFO",
            interval=ModInputInterval[type.name].value,
            org_id=org_id,
            # Organizations typically generate high alert volumes; using 4-hour time window
            # ensures alerts are fetched frequently to avoid large batch processing
            time_window=4 if type == ModInputType.ALERT_DASHBOARD_INDEX else None,
        )
        self._mod_inputs_mgr.create_input(
            input_name=f"{type.value}_{org_id}", config=config, input_kind=type
        )

    def _update_mod_input(self, type: ModInputType, org_id: str, index: str):
        """
        Update an existing modular input configuration.

        Updates the configuration of an existing Splunk modular input,
        typically to change the target index for data collection.

        Args:
            type (ModInputType): The type of modular input to update
                (PRIVATE_APPS or APP_DISCOVERY).
            org_id (str): The organization ID identifying the input.
            index (str): The new Splunk index for data storage.
        """
        config = ModularInputConfig(index=index, log_level="INFO", org_id=org_id)
        self._mod_inputs_mgr.update_input(
            input_name=f"{type.value}_{org_id}", config=config, input_kind=type
        )

    def _delete_mod_input(self, type: ModInputType, org_id: str):
        """
        Delete a modular input for a specific organization.

        Removes the Splunk modular input associated with the specified
        type and organization. Silently handles cases where the input
        has already been deleted.

        Args:
            type (ModInputType): The type of modular input to delete
                (PRIVATE_APPS or APP_DISCOVERY).
            org_id (str): The organization ID identifying the input to delete.
        """
        try:
            self._mod_inputs_mgr.delete_input(
                input_name=f"{type.value}_{org_id}", input_kind=type
            )
        except ModularInputNotFoundException as e:
            self._logger.error(
                f"Modular input not found for deletion: {str(e)}. Assuming already deleted."
            )

    def _delete_mod_inputs(self, org_id: str):
        """
        Delete all modular inputs for a specific organization.

        Removes private apps, app discovery, and alert dashboard index
        modular inputs associated with the organization.

        Args:
            org_id (str): The organization ID whose modular inputs to delete.
        """
        self._delete_mod_input(ModInputType.PRIVATE_APPS, org_id)
        self._delete_mod_input(ModInputType.APP_DISCOVERY, org_id)
        self._delete_mod_input(ModInputType.ALERT_DASHBOARD_INDEX, org_id)

    def _store_credentials(
        self,
        org_id: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        """
        Store API credentials securely in Splunk's password storage.

        Saves the API key, API secret, and access token to Splunk's
        secure credential storage, associated with the organization ID.
        All three credentials must be provided; if any is None, no
        credentials are stored.

        Args:
            org_id (str): The organization ID to associate with credentials.
            api_key (Optional[str], optional): The API key to store. Defaults to None.
            api_secret (Optional[str], optional): The API secret to store. Defaults to None.
            access_token (Optional[str], optional): The access token to store. Defaults to None.
        """
        if api_key is None or api_secret is None or access_token is None:
            return
        if api_key:
            TokenService.set_token(
                self._session_token, api_key, "api_key", org_id=org_id
            )
        if api_secret:
            TokenService.set_token(
                self._session_token, api_secret, "api_secret", org_id=org_id
            )
        if access_token:
            TokenService.set_token(
                self._session_token, access_token, "access_token", org_id=org_id
            )

    def _delete_credentials(self, org_id: str):
        """
        Delete all stored credentials for a specific organization.

        Removes the API key, API secret, and access token from Splunk's
        secure credential storage for the specified organization.

        Args:
            org_id (str): The organization ID whose credentials to delete.
        """
        TokenService.delete_token(self._session_token, "api_key", org_id=org_id)
        TokenService.delete_token(self._session_token, "api_secret", org_id=org_id)
        TokenService.delete_token(self._session_token, "access_token", org_id=org_id)
