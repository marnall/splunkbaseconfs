"""This module provides functionality to update indicator status in CTIX via Splunk workflow actions."""
import ta_cyware_ctix_declare  # noqa: F401

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import ta_cyware_ctix.logging_helper as logging_helper
import ta_cyware_ctix.proxy_helper as proxy_helper
import ta_cyware_ctix.ssl_helper as ssl_helper
import ta_cyware_ctix.conf_helper as conf_helper
from ta_cyware_ctix.ctix_exceptions import (
    CTIXAPIError, CTIXConnectionError, CTIXTimeoutError, CTIXConfigurationError, CTIXValidationError
)
from ta_cyware_ctix.ctix_connector import CTIXConnector as BaseCTIXConnector
from ta_cyware_ctix.constants import DEFAULT_TIMEOUT, USER_AGENT

import json
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from ta_cyware_ctix.aob_py3 import requests


logger = logging_helper.get_logger("update_indicator_status")


class CTIXConnector(BaseCTIXConnector):
    """CTIX connector for update indicator status operations."""

    def update_indicator_status(self, status_type, ctix_id, indicator_name, undeprecate_until_epoch):
        """
        Update indicator status in CTIX using bulk-action endpoints.

        Args:
            status_type: Status field to update (is_whitelist, is_reviewed, is_revoked, etc.)
            ctix_id: CTIX indicator ID (UUID)
            indicator_name: Indicator name
            undeprecate_until_epoch: Undeprecate until epoch

        Returns:
            dict: API response
        """
        try:
            # Map status types to API endpoints
            status_endpoint_map = {
                "deprecate": "deprecate",
                "un_deprecate": "un_deprecate",
                "false_positive": "false_positive",
                "un_false_positive": "un_false_positive",
                "reviewed": "reviewed",
                "manual_review": "manual_review",
                "revoke": "revoke",
                "action": "action"
            }

            if status_type not in status_endpoint_map:
                raise CTIXValidationError(
                    f"Invalid status_type '{status_type}'. Must be one of: {', '.join(status_endpoint_map.keys())}"
                )

            endpoint = status_endpoint_map[status_type]
            url = f"{self.api_url}/ingestion/threat-data/bulk-action/{endpoint}/"
            auth_params = self.auth()

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': USER_AGENT,
            }

            payload = {
                "object_type": "indicator",
                "object_ids": [ctix_id]
            }
            if status_type == "un_deprecate":
                payload["data"] = {"undeprecate_until": undeprecate_until_epoch}

            # For watchlist (watchlist), add the indicator name in data field
            if status_type == "watchlist":
                if not indicator_name:
                    raise CTIXValidationError("Indicator name is required for watchlist operation")
                payload["data"] = {
                    "name": [indicator_name]
                }

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            logger.debug(f"API URL: {url}")
            logger.debug(f"API payload: {json.dumps(payload)}")

            response = requests.post(
                url=url,
                params=auth_params,
                headers=headers,
                json=payload,
                proxies=proxy_config,
                verify=ssl_verify,
                timeout=DEFAULT_TIMEOUT
            )

            if response.ok:
                logger.info(f"Successfully updated status to {status_type} for indicator {ctix_id}")
                try:
                    result = response.json()
                    return result
                except json.JSONDecodeError:
                    logger.info("Returning success status to UI")
                    return {"status": "success", "message": response.text}
            else:
                logger.error(f"Failed to update indicator status - Status: {response.status_code}")
                raise CTIXAPIError(
                    f"API Error - URL: {url} - Status Code: {response.status_code}, Message: {response.text}"
                )
        except requests.exceptions.Timeout as e:
            raise CTIXTimeoutError(f"Request to CTIX API timed out after {DEFAULT_TIMEOUT} seconds") from e
        except requests.exceptions.ConnectionError as e:
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError, CTIXValidationError):
            raise
        except Exception as e:
            logger.error(
                f"Error updating indicator status: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error updating indicator status: {str(e)}") from e


@Configuration()
class CTIXUpdateIndicatorStatusCommand(GeneratingCommand):
    """Generating command class for updating the indicator status in CTIX."""

    status_type = Option(require=False, default="is_reviewed")
    value = Option(require=False, default=None)
    indicator_name = Option(require=False, default=None)
    splunk_account = Option(require=False, default=None)
    undeprecate_until = Option(require=False, default="")

    def generate(self):
        """Generate results for updating the indicator status in CTIX."""
        try:
            # ===== Get Configuration =====
            # Multi-account: Get credentials for the specified account via REST call
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

            # Get command parameters
            status_type = self.status_type if self.status_type else 'is_reviewed'
            ctix_id = self.value
            indicator_name = self.indicator_name

            # Validate CTIX ID
            if not ctix_id:
                raise CTIXValidationError("Cyware ID (value) is required. Please provide the indicator's CTIX ID.")

            # Call CTIX API
            logger.info(f"Updating Status for ID: '{ctix_id}' to '{status_type}'.")

            days = int(self.undeprecate_until)
            current_time = datetime.now(timezone.utc)
            future_time = current_time + timedelta(days=days)
            undeprecate_until_epoch = int(future_time.timestamp())

            result = CTIXConnector(api_url, client_id, client_secret, session_key).update_indicator_status(
                status_type=status_type,
                ctix_id=ctix_id,
                indicator_name=indicator_name,
                undeprecate_until_epoch=undeprecate_until_epoch
            )

            # Format output
            output = {
                "status_type": status_type,
                "ctix_id": ctix_id,
                "status": "success",
                "message": f"Successfully updated {status_type} for indicator.",
                "_time": time.time(),
                "_raw": json.dumps(result)
            }

            # Add API response details if available
            if isinstance(result, dict):
                for key, value in result.items():
                    if key not in output:
                        output[key] = value

            yield output

        except Exception as err:
            logger.error(f"Update Status Error: {str(err)}")
            yield {
                "status_type": getattr(self, 'status_type', 'unknown'),
                "ctix_id": getattr(self, 'value', 'unknown'),
                "status": "error",
                "message": str(err),
                "_raw": json.dumps({"error": str(err)}),
                "_time": time.time()
            }
            logger.error(err)


if __name__ == "__main__":
    dispatch(CTIXUpdateIndicatorStatusCommand, sys.argv, sys.stdin, sys.stdout, __name__)
