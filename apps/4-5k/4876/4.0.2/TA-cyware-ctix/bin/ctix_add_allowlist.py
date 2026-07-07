"""Add indicators to CTIX allowlist."""

import ta_cyware_ctix_declare  # noqa: F401

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import ta_cyware_ctix.logging_helper as logging_helper
import ta_cyware_ctix.proxy_helper as proxy_helper
import ta_cyware_ctix.ssl_helper as ssl_helper
import ta_cyware_ctix.conf_helper as conf_helper
from ta_cyware_ctix.ctix_exceptions import (
    CTIXAPIError, CTIXConnectionError, CTIXTimeoutError, CTIXConfigurationError, CTIXValidationError
)
from ta_cyware_ctix.constants import (
    COLLECTION_BASE_NAME, MATCHED_COLLECTION_BASE_NAME, DEFAULT_TIMEOUT, INDICATOR_TYPE_MAPPING,
    VALID_INDICATOR_TYPES, MASTER_LOOKUP_DICT, MATCHED_LOOKUP_DICT, USER_AGENT
)
from ta_cyware_ctix.ctix_connector import CTIXConnector as BaseCTIXConnector
from ta_cyware_ctix.kvstore_helper import CollectionManager

import json
import sys
import time
from ta_cyware_ctix.aob_py3 import requests
import re


logger = logging_helper.get_logger("update_allowlist")
header_constant = {
    'Content-Type': 'application/json',
    'User-Agent': USER_AGENT,
}
exception_msg = f"Request to CTIX API timed out after {DEFAULT_TIMEOUT} seconds"


class CTIXConnector(BaseCTIXConnector):
    """CTIX connector for allowlist operations."""

    def get_indicator_details_by_value(self, indicator_type, indicator_value):
        """
        Get indicator details by value and type.

        Args:
            indicator_type: Type of indicator (user-friendly name or backend value)
            indicator_value: Value of the indicator

        Returns:
            dict: Indicator details including ID
        """
        try:
            # Map user-friendly indicator type to backend value
            mapped_type = INDICATOR_TYPE_MAPPING.get(indicator_type, indicator_type)

            if mapped_type not in VALID_INDICATOR_TYPES:
                logger.warning(
                    f"Indicator type '{indicator_type}' is not supported. "
                    f"Valid types: {', '.join(INDICATOR_TYPE_MAPPING.keys())}"
                )
                raise CTIXValidationError(
                    f"Invalid indicator type: {indicator_type}. "
                    f"Please use one of: {', '.join(INDICATOR_TYPE_MAPPING.keys())}"
                )

            logger.debug(f"Mapped indicator type '{indicator_type}' to '{mapped_type}'")

            url = f"{self.api_url}/ingestion/threat-data/"
            auth_params = self.auth()
            auth_params["type"] = mapped_type
            auth_params["value"] = indicator_value

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            logger.debug(f"Get Indicator Details by Value - URL: {url}")
            logger.debug(f"Get Indicator Details by Value - Params: {auth_params}")

            response = requests.get(
                url=url,
                params=auth_params,
                headers=header_constant,
                proxies=proxy_config,
                verify=ssl_verify,
                timeout=DEFAULT_TIMEOUT
            )
            response.raise_for_status()

            result = response.json()

            # If results is a list, return the first item
            if isinstance(result, dict) and "results" in result:
                results = result["results"]
                if results and len(results) > 0:
                    return results[0]
            elif isinstance(result, list) and len(result) > 0:
                return result[0]
            elif isinstance(result, dict):
                return result

            return None

        except requests.exceptions.Timeout as e:
            raise CTIXTimeoutError(exception_msg) from e
        except requests.exceptions.ConnectionError as e:
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError):
            raise
        except Exception as e:
            raise CTIXAPIError(f"Error getting indicator details: {str(e)}") from e

    def add_to_allowlist_by_value(self, indicator_type, values, reason):
        """
        Add indicators to allowlist using indicator value and type.

        Args:
            indicator_type: Type of indicator (user-friendly name or backend value)
            values: List of indicator values to add
            reason: Reason for adding to allowlist

        Returns:
            dict: API response
        """
        try:
            # Map user-friendly indicator type to backend value
            mapped_type = INDICATOR_TYPE_MAPPING.get(indicator_type, indicator_type)

            if mapped_type not in VALID_INDICATOR_TYPES:
                logger.warning(
                    f"Indicator type '{indicator_type}' is not supported. "
                    f"Valid types: {', '.join(INDICATOR_TYPE_MAPPING.keys())}"
                )
                raise CTIXValidationError(
                    f"Invalid indicator type: {indicator_type}. "
                    f"Please use one of: {', '.join(INDICATOR_TYPE_MAPPING.keys())}"
                )

            logger.debug(f"Mapped indicator type '{indicator_type}' to '{mapped_type}'")

            url = f"{self.api_url}/conversion/allowed_indicators/"
            auth_params = self.auth()

            payload = {
                "type": mapped_type,
                "values": values,
                "reason": reason
            }

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            logger.debug(f"Add to Allowlist by Value - URL: {url}")
            logger.debug(f"Add to Allowlist by Value - Payload: {json.dumps(payload)}")

            response = requests.post(
                url=url,
                params=auth_params,
                headers=header_constant,
                json=payload,
                proxies=proxy_config,
                verify=ssl_verify,
                timeout=DEFAULT_TIMEOUT
            )
            response.raise_for_status()

            result = response.json()

            # Check if any indicators were invalid for the selected type
            if result.get('details', {}).get('invalid'):
                invalid_indicators = result['details']['invalid']
                raise CTIXValidationError(
                    f"The following indicators do not match the selected type '{mapped_type}': "
                    f"{', '.join(invalid_indicators)}"
                )

            return result

        except requests.exceptions.Timeout as e:
            raise CTIXTimeoutError(exception_msg) from e
        except requests.exceptions.ConnectionError as e:
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError):
            raise
        except Exception as e:
            raise CTIXAPIError(f"Error adding to allowlist: {str(e)}") from e

    def remove_from_allowlist(self, ctix_id):
        """
        Remove an indicator from allowlist in CTIX using bulk-actions API.

        Args:
            ctix_id: CTIX indicator ID (UUID)

        Returns:
            dict: API response
        """
        logger.info(f"Remove from allowlist action started for indicator ID: {ctix_id}")

        try:
            url = f"{self.api_url}/conversion/allowed_indicators/bulk-actions/"
            auth_params = self.auth()

            payload = {
                "ids": [ctix_id],
                "action": "delete"
            }

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            logger.info(f"Calling API to remove indicator from allowlist: {url}")
            logger.debug(f"API payload: {json.dumps(payload)}")

            response = requests.post(
                url=url,
                params=auth_params,
                headers=header_constant,
                json=payload,
                proxies=proxy_config,
                verify=ssl_verify,
                timeout=DEFAULT_TIMEOUT
            )

            if response.ok:
                logger.info(f"Successfully removed indicator {ctix_id} from allowlist")
                try:
                    result = response.json()
                    return result
                except json.JSONDecodeError:
                    return {"status": "success", "message": "Indicator removed from allowlist successfully"}
            else:
                logger.error(f"Failed to remove indicator from allowlist - Status: {response.status_code}")
                raise CTIXAPIError(
                    f"API Error - URL: {url} - Status Code: {response.status_code}, Message: {response.text}"
                )
        except requests.exceptions.Timeout as e:
            raise CTIXTimeoutError(exception_msg) from e
        except requests.exceptions.ConnectionError as e:
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError):
            raise
        except Exception as e:
            raise CTIXAPIError(f"Error removing from allowlist: {str(e)}") from e

    def get_indicator_details(self, ctix_id):
        """
        Fetch indicator details from CTIX API to determine its type.

        Args:
            ctix_id: CTIX indicator ID (UUID)

        Returns:
            dict: Indicator details including type
        """
        try:
            url = f"{self.api_url}/ingestion/threat-data/details/"
            auth_params = self.auth()
            auth_params["object_id"] = ctix_id
            auth_params["object_type"] = "indicator"

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            logger.debug(f"Get Indicator Details - URL: {url}")

            response = requests.get(
                url=url,
                params=auth_params,
                headers=header_constant,
                proxies=proxy_config,
                verify=ssl_verify,
                timeout=DEFAULT_TIMEOUT
            )

            if response.ok:
                data = response.json()
                return data
            else:
                raise CTIXAPIError(
                    f"Cyware API Error - URL: {url} - Status Code: {response.status_code}, Message: {response.text}"
                )
        except requests.exceptions.Timeout as e:
            raise CTIXTimeoutError(exception_msg) from e
        except requests.exceptions.ConnectionError as e:
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError):
            raise
        except Exception as e:
            raise CTIXAPIError(f"Error adding to allowlist: {str(e)}") from e


@Configuration()
class CTIXUpdateAllowlistCommand(GeneratingCommand):
    """Command to add indicators to CTIX allowlist."""

    indicator_value = Option(require=False, default=None)
    indicator_type = Option(require=False, default=None)
    ctix_id = Option(require=False, default=None)
    action = Option(require=False, default="add")
    reason = Option(require=False, default="")
    splunk_account = Option(require=False, default=None)
    kvstore_update = Option(require=False, default="false")

    def _map_indicator_type_to_collection_name(self, indicator_type):
        """
        Map indicator type to collection name format.

        Args:
            indicator_type: User-friendly indicator type (e.g., "Ipv4 addr")

        Returns:
            str: Collection name format (e.g., "ipv4_addr")
        """
        # Mapping from user-friendly names to collection names
        type_mapping = {
            "Artifact": "artifact",
            "Autonomous system": "autonomous_system",
            "Directory": "directory",
            "Domain": "domain_name",
            "Email addr": "email_addr",
            "Email message": "email_message",
            "File": "file",
            "Ipv4 addr": "ipv4_addr",
            "Ipv6 addr": "ipv6_addr",
            "Mac addr": "mac_addr",
            "MD5": "file",
            "Mutex": "mutex",
            "Network traffic": "network_traffic",
            "Process": "process",
            "SHA1": "file",
            "SHA224": "file",
            "SHA256": "file",
            "SHA384": "file",
            "SHA512": "file",
            "SHA3224": "file",
            "SHA3256": "file",
            "SHA3384": "file",
            "SHA3512": "file",
            "Software": "software",
            "SSDEEP": "file",
            "URL": "url",
            "User account": "user_account",
            "Windows registry key": "windows_registry_key",
            "X509 certificate": "x509_certificate",
            "YARA": "yara"
        }

        return type_mapping.get(indicator_type, indicator_type.lower().replace(" ", "_"))

    def normalize_indicator_type(self, indicator_type):
        """
        Normalize indicator type for collection naming (same logic as input module).

        Args:
            indicator_type: Raw indicator type from API

        Returns:
            str: Normalized indicator type safe for collection names
        """
        if not indicator_type or str(indicator_type).strip() == "":
            return "unknown"

        # Convert to string and normalize
        normalized = str(indicator_type).strip().lower()

        # Remove/replace special characters that aren't allowed in collection names
        normalized = re.sub(r"\W", "_", normalized)

        # Remove multiple consecutive underscores
        normalized = re.sub(r"_+", "_", normalized)

        # Remove leading/trailing underscores
        normalized = normalized.strip("_")

        # Ensure it's not empty after normalization
        if not normalized:
            return "unknown"

        return normalized

    def _get_collection_names(self, indicator_type):
        """Get the list of collection names for an indicator type."""
        collection_suffix = self._map_indicator_type_to_collection_name(indicator_type)

        # Get main collection (TI data)
        main_collection = (
            MASTER_LOOKUP_DICT.get(collection_suffix) or
            f"{COLLECTION_BASE_NAME}_{collection_suffix}"
        )

        # Get matched collection (matched indicators)
        matched_collection = (
            MATCHED_LOOKUP_DICT.get(collection_suffix) or
            f"{MATCHED_COLLECTION_BASE_NAME}_{collection_suffix}"
        )

        return [main_collection, matched_collection]

    def update_kvstore(self, session_key, indicator_value, action, indicator_type):
        """
        Delete entries from KV store collections based on indicator value.

        Deletes entries from both master and matched indicator collections.

        Args:
            session_key: Splunk session key
            indicator_value: Indicator value to delete
            action: 'add' or 'remove' from allowlist (not used, always deletes)
            indicator_type: Type of indicator (domain, ip, file, etc.)

        Returns:
            dict: Status of KV store update
        """
        try:
            # Get collection names using existing logic
            collection_names = self._get_collection_names(indicator_type)
            logger.info(f"Deleting from KVStore collections: {collection_names}")

            deleted_count = 0
            deleted_collections = []
            errors = []

            # Process each collection using CollectionManager
            for collection_name in collection_names:
                try:
                    # Create CollectionManager for this collection
                    collection_mgr = CollectionManager(
                        collection_name=collection_name,
                        session_key=session_key
                    )

                    # First check if records exist before deletion
                    query = {"indicator": indicator_value}
                    existing_records = collection_mgr.get(query=query)

                    deleted = 0
                    if existing_records:
                        # Records exist, proceed with deletion
                        collection_mgr.delete_batch(query)

                        # Verify deletion was successful
                        remaining = collection_mgr.get(query=query)
                        deleted = len(existing_records) if not remaining else 0
                    else:
                        # No records found to delete
                        deleted = 0

                    deleted_count += deleted
                    if deleted > 0:
                        deleted_collections.append(collection_name)
                        logger.info(f"Deleted {deleted} records from {collection_name}")
                    else:
                        logger.info(f"No records found in {collection_name}")

                except Exception as e:
                    error_msg = f"Error processing collection {collection_name}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

            # Build result
            if errors and not deleted_collections:
                return {
                    "status": "error",
                    "message": "; ".join(errors),
                    "updated_count": 0,
                    "collections": []
                }
            elif errors:
                return {
                    "status": "partial_success",
                    "message": f"Successfully deleted {deleted_count} records. Errors: {'; '.join(errors)}",
                    "updated_count": deleted_count,
                    "collections": deleted_collections
                }
            elif deleted_count == 0:
                return {
                    "status": "not_found",
                    "message": "No local records found with this indicator value",
                    "updated_count": 0,
                    "collections": []
                }
            else:
                return {
                    "status": "success",
                    "message": f"Successfully deleted {deleted_count} records from KVStore collections",
                    "updated_count": deleted_count,
                    "collections": deleted_collections
                }

        except Exception as e:
            logger.error(f"Error updating KV Store: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"KV Store update failed: {str(e)}",
                "updated_count": 0,
                "collections": []
            }

    def _extract_indicator_type(self, indicator_details):
        """Extract indicator type from API response."""
        if not isinstance(indicator_details, dict):
            return None

        if "indicator_type" in indicator_details:
            indicator_type_obj = indicator_details.get("indicator_type")
            if isinstance(indicator_type_obj, dict):
                return indicator_type_obj.get("type")
            return indicator_type_obj

        if "type" in indicator_details:
            return indicator_details.get("type")

        if "data" in indicator_details:
            data = indicator_details.get("data", {})
            if isinstance(data, dict):
                indicator_type_obj = data.get("indicator_type", {})
                if isinstance(indicator_type_obj, dict):
                    return indicator_type_obj.get("type")
                return indicator_type_obj

        return None

    def _handle_kvstore_update(self, connector, session_key, action):
        """Handle KVStore update logic."""
        kvstore_result = None
        kvstore_status = "not_attempted"
        kvstore_message = "KVStore update not requested"

        if not self.kvstore_update or str(self.kvstore_update).lower() != "true":
            return kvstore_result, kvstore_status, kvstore_message

        logger.info(
            f"KV Store update enabled - using indicator_value={self.indicator_value},"
            f"indicator_type={self.indicator_type}"
        )
        try:
            kvstore_result = self.update_kvstore(session_key, self.indicator_value, action, self.indicator_type)
            logger.info(f"KV Store update result: {kvstore_result}")

            if kvstore_result.get("status") == "success":
                kvstore_status = "success"
                kvstore_message = kvstore_result.get('message', 'Updated successfully')
            elif kvstore_result.get("status") == "not_found":
                kvstore_status = "not_found"
                kvstore_message = "No local records found with this indicator value"
            else:
                kvstore_status = "error"
                kvstore_message = kvstore_result.get('message', 'Update failed')
        except Exception as e:
            logger.error(f"KVStore update failed but CTIX update succeeded: {str(e)}", exc_info=True)
            kvstore_status = "error"
            kvstore_message = f"Failed to update KVStore: {str(e)}"
            kvstore_result = {
                "status": "error",
                "message": kvstore_message,
                "updated_count": 0,
                "collections": []
            }

        return kvstore_result, kvstore_status, kvstore_message

    def _get_ctix_status(self, result):
        """Extract status from API response."""
        if isinstance(result, dict) and "status" in result:
            return result["status"]
        return "success"

    def _get_ctix_message(self, action, result, indicator_value=None):
        """Get CTIX message from result or use default."""
        default_message = (
            f"Indicator '{indicator_value}' successfully added to allowlist"
            if action == "add"
            else f"Indicator '{indicator_value}' successfully removed from allowlist"
        )

        if isinstance(result, dict) and "message" in result:
            return result["message"]
        return default_message

    def _format_user_message(self, ctix_message, kvstore_status, kvstore_message):
        """Format user-friendly message with KVStore status."""
        if kvstore_status in ["success", "error", "not_found"]:
            return f"{ctix_message} | KVStore: {kvstore_message}"
        return ctix_message

    def _add_kvstore_fields(self, output, kvstore_result):
        """Add KVStore related fields to output."""
        if kvstore_result:
            output["kvstore_updated_count"] = kvstore_result.get("updated_count", 0)
            output["kvstore_collections"] = ", ".join(kvstore_result.get("collections", []))
        else:
            output["kvstore_updated_count"] = 0
            output["kvstore_collections"] = ""

    def _add_indicator_type_fields(self, output):
        """Add indicator type fields to output."""
        if self.indicator_type:
            output["indicator_type"] = self.indicator_type
            mapped_type = INDICATOR_TYPE_MAPPING.get(self.indicator_type, self.indicator_type)
            if mapped_type:
                output["indicator_type_backend"] = mapped_type

    def _merge_result_fields(self, output, result):
        """Merge additional fields from result into output."""
        if isinstance(result, dict):
            for key, value in result.items():
                if key not in output:
                    output[key] = value

    def _build_output(
        self, action, reason, result, kvstore_result, kvstore_status, kvstore_message, indicator_value=None
    ):
        """Build output dictionary."""
        ctix_status = self._get_ctix_status(result)
        ctix_message = self._get_ctix_message(action, result, indicator_value)
        friendly_message = self._format_user_message(ctix_message, kvstore_status, kvstore_message)

        output = {
            "action": action,
            "reason": reason if action == "add" else "",
            "status": ctix_status,
            "ctix_status": ctix_status,
            "ctix_message": ctix_message,
            "kvstore_status": kvstore_status,
            "kvstore_message": kvstore_message,
            "message": friendly_message,
            "_time": time.time(),
            "_raw": json.dumps(result)
        }

        self._add_indicator_type_fields(output)
        self._add_kvstore_fields(output, kvstore_result)
        self._merge_result_fields(output, result)

        return output

    def _get_friendly_error(self, error_msg):
        """Convert error message to user-friendly format."""
        if "Credentials missing" in error_msg:
            return "Account credentials not configured. Please check your Splunk account settings."
        if (
            "Both indicator value and type are required" in error_msg
            or "Either CTIX Indicator ID or both indicator value and type are required" in error_msg
        ):
            return "Please provide both indicator value and indicator type."
        if "Invalid action" in error_msg:
            return "Invalid action selected. Please choose 'add' or 'remove'."
        return error_msg

    def _get_credentials(self):
        """Fetch and validate account credentials."""
        logger.debug(f"Fetching credentials for account: {self.splunk_account}")
        session_key = self._metadata.searchinfo.session_key
        account_creds = conf_helper.get_account_credentials_for_search_command(
            self.splunk_account, logger, session_key
        )
        logger.info(f"Successfully fetched credentials for account: {self.splunk_account}")

        api_url = account_creds.get("base_url")
        client_id = account_creds.get("access_id")
        client_secret = account_creds.get("secret_key")

        if not client_id or not client_secret or not api_url:
            raise CTIXConfigurationError(
                "Credentials missing. Please configure base_url, access_id, and "
                "secret_key in Add-on Settings or select a valid account."
            )

        return api_url, client_id, client_secret, session_key

    def _execute_add_action(self, connector):
        """Execute add action and return result."""
        reason = self.reason if self.reason else "Added from Splunk"

        if self.indicator_value and self.indicator_type:
            # Use new API with indicator value and type
            logger.info(f"Allowlist Action: add for indicator value: {self.indicator_value}")
            result = connector.add_to_allowlist_by_value(
                indicator_type=self.indicator_type,
                values=[self.indicator_value],
                reason=reason
            )
        else:
            raise CTIXValidationError(
                "Both indicator value and type are required for add action"
            )

        return result

    def _build_error_output(self, err):
        """Build error output dictionary."""
        logger.error(f"Allowlist Error: {str(err)}")
        friendly_error = self._get_friendly_error(str(err))

        output = {
            "action": getattr(self, 'action', 'unknown'),
            "reason": getattr(self, 'reason', ''),
            "status": "error",
            "message": friendly_error,
            "_raw": json.dumps({"error": str(err)}),
            "_time": time.time()
        }

        # Add indicator type fields if available
        if self.indicator_type:
            output["indicator_type"] = self.indicator_type
            mapped_type = INDICATOR_TYPE_MAPPING.get(self.indicator_type, self.indicator_type)
            if mapped_type:
                output["indicator_type_backend"] = mapped_type

        return output

    def generate(self):
        """Generate command results."""
        try:
            api_url, client_id, client_secret, session_key = self._get_credentials()
            connector = CTIXConnector(api_url, client_id, client_secret, session_key)

            action = self.action if self.action else "add"
            reason = self.reason if self.reason else "Added from Splunk"

            # Execute the appropriate action
            if action == "remove":
                logger.info(f"Allowlist Action: remove for ctix_id: {self.ctix_id}")
                result = connector.remove_from_allowlist(ctix_id=self.ctix_id)
            elif action == "add":
                result = self._execute_add_action(connector)
            else:
                raise CTIXValidationError(f"Invalid action '{action}'. Must be one of: add, remove")

            # Handle KVStore update
            kvstore_result, kvstore_status, kvstore_message = self._handle_kvstore_update(
                connector, session_key, action
            )

            output = self._build_output(
                action, reason, result, kvstore_result, kvstore_status, kvstore_message,
                self.indicator_value
            )

            yield output

        except Exception as err:
            yield self._build_error_output(err)
            logger.error(err)


if __name__ == "__main__":
    dispatch(CTIXUpdateAllowlistCommand, sys.argv, sys.stdin, sys.stdout, __name__)
