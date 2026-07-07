"""Manage tags for CTIX indicators."""

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
from ta_cyware_ctix.aob_py3 import requests
import re


logger = logging_helper.get_logger("manage_tags")
CONTENT_TYPE_JSON = 'application/json'
TIMEOUT_MESSAGE = f"Request to CTIX API timed out after {DEFAULT_TIMEOUT} seconds"
header_constant = {
    'Content-Type': CONTENT_TYPE_JSON,
}
exception_msg = TIMEOUT_MESSAGE


class CTIXConnector(BaseCTIXConnector):
    """CTIX connector for manage tags operations."""

    def _process_tag_inputs(self, tag_ids):
        """Process tag inputs and create new tags if needed."""
        tag_input_list = [tag_id.strip() for tag_id in tag_ids.split(',') if tag_id.strip()]
        UUID_REGEX = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')

        if not tag_input_list:
            raise CTIXValidationError("No valid tag IDs provided")

        tag_id_list = []
        for tag in tag_input_list:
            if UUID_REGEX.match(tag):
                tag_id_list.append(tag)
            else:
                logger.info(f"Creating new tag: {tag}")
                new_tag_id = self.create_new_tag_in_cyware(tag)
                tag_id_list.append(new_tag_id)

        return tag_id_list

    def _merge_existing_tags(self, tag_id_list, ctix_id):
        """Merge existing tags with the provided tag list."""
        existing_tags = self.get_indicator_tags(ctix_id)
        if existing_tags:
            existing_tag_ids = [tag.get("id") for tag in existing_tags if tag.get("id")]
            tag_id_list.extend(existing_tag_ids)
            logger.info(f"Added {len(existing_tag_ids)} existing tags to the list")

        # Remove duplicates while preserving order
        seen = set()
        unique_tag_ids = []
        for tag_id in tag_id_list:
            if tag_id not in seen:
                seen.add(tag_id)
                unique_tag_ids.append(tag_id)

        logger.info(f"Final tag_ids after adding existing tags: {unique_tag_ids}")
        return unique_tag_ids

    def _build_tag_payload(self, action, ctix_id, tag_id_list):
        """Build payload for tag management API."""
        if action == "add_tags":
            url = f"{self.api_url}/ingestion/threat-data/action/update_tag/"
            payload = {
                "object_type": "indicator",
                "object_id": ctix_id,
                "data": {
                    "tag_ids": tag_id_list
                }
            }
        else:  # remove_tags
            url = f"{self.api_url}/ingestion/threat-data/bulk-action/remove_tag/"
            payload = {
                "object_type": "indicator",
                "object_ids": [ctix_id],
                "data": {
                    "tag_ids": tag_id_list
                }
            }

        return url, payload

    def _make_tag_api_request(self, url, payload, auth_params, headers, proxy_config, ssl_verify):
        """Make API request to manage tags."""
        logger.debug(f"Manage Tags - URL: {url}")
        logger.debug(f"Manage Tags - Payload: {json.dumps(payload)}")

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
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"status": "success", "message": response.text}
        else:
            raise CTIXAPIError(
                f"Cyware API Error - URL: {url} - Status Code: {response.status_code}, Message: {response.text}"
            )

    def manage_tags(self, ctix_id, action, tag_ids):
        """
        Add, remove, or replace tags for an indicator in CTIX.

        Args:
            ctix_id: CTIX indicator ID (UUID)
            action: add_tags, remove_tags, or replace_tags
            tag_ids: Comma-separated tag IDs

        Returns:
            dict: API response
        """
        logger.info(f"Manage tags action started - {action} for indicator ID: {ctix_id}")

        try:
            if action not in ["add_tags", "remove_tags"]:
                raise CTIXValidationError(
                    f"Invalid action '{action}'. Must be one of: add_tags, remove_tags"
                )

            # Process tag inputs
            tag_id_list = self._process_tag_inputs(tag_ids)
            logger.info(f"Processing {len(tag_id_list)} tags for {action}")

            # For add action, merge with existing tags
            if action == "add_tags":
                logger.info("Merging with existing tags")
                tag_id_list = self._merge_existing_tags(tag_id_list, ctix_id)

            # Build payload and make API request
            auth_params = self.auth()
            headers = {'Content-Type': CONTENT_TYPE_JSON, 'User-Agent': USER_AGENT}
            url, payload = self._build_tag_payload(action, ctix_id, tag_id_list)

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            logger.info(f"Calling API to {action} for indicator: {ctix_id}")
            logger.debug(f"API URL: {url}")
            logger.debug(f"API payload: {json.dumps(payload)}")

            result = self._make_tag_api_request(url, payload, auth_params, headers, proxy_config, ssl_verify)
            logger.info(f"Successfully {action.replace('_tags', 'ed tags')} for indicator {ctix_id}")
            return result

        except requests.exceptions.Timeout as e:
            raise CTIXTimeoutError(TIMEOUT_MESSAGE) from e
        except requests.exceptions.ConnectionError as e:
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError, CTIXValidationError):
            raise
        except Exception as e:
            logger.error(
                f"Error managing tags: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error managing tags: {str(e)}") from e

    def create_new_tag_in_cyware(self, tag_name):
        """
        Create a new tag in CTIX.

        Args:
            tag_name: Name of the tag to create

        Returns:
            str: The ID of the created tag
        """
        try:
            url = f"{self.api_url}/ingestion/tags/"
            auth_params = self.auth()
            headers = {
                'Content-Type': CONTENT_TYPE_JSON,
                'Accept': CONTENT_TYPE_JSON,
                'User-Agent': USER_AGENT
            }

            payload = {
                "name": tag_name
            }

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            logger.debug(f"Create Tag - URL: {url}")
            logger.debug(f"Create Tag - Payload: {json.dumps(payload)}")

            response = requests.post(
                url=url,
                params=auth_params,
                headers=headers,
                json=payload,
                proxies=proxy_config,
                verify=ssl_verify,
                timeout=DEFAULT_TIMEOUT
            )
            response.raise_for_status()

            result = response.json()

            if "id" in result:
                logger.info(f"Successfully created tag '{tag_name}' with ID: {result['id']}")
                return result["id"]
            else:
                raise CTIXAPIError("Tag creation response did not contain an ID")

        except requests.exceptions.Timeout as e:
            raise CTIXTimeoutError(TIMEOUT_MESSAGE) from e
        except requests.exceptions.ConnectionError as e:
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError, CTIXValidationError):
            raise
        except Exception as e:
            logger.error(
                f"Error creating tag: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error creating tag: {str(e)}") from e

    def get_indicator_tags(self, ctix_id):
        """
        Fetch tags for a specific indicator from CTIX.

        Args:
            ctix_id: CTIX indicator ID (UUID)

        Returns:
            list: List of tags associated with the indicator
        """
        try:
            url = f"{self.api_url}/ingestion/threat-data/indicator/{ctix_id}/basic/"
            auth_params = self.auth()

            headers = {
                'Content-Type': CONTENT_TYPE_JSON,
                'User-Agent': USER_AGENT
            }

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            logger.debug(f"Get Indicator Tags - URL: {url}, Indicator ID: {ctix_id}")

            response = requests.get(
                url=url,
                params=auth_params,
                headers=headers,
                proxies=proxy_config,
                verify=ssl_verify,
                timeout=DEFAULT_TIMEOUT
            )

            if response.ok:
                try:
                    result = response.json()
                    if isinstance(result, dict):
                        tags = result.get('tags', [])
                        return tags
                    else:
                        return []
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing response: {str(e)}")
                    return []
            else:
                raise CTIXAPIError(
                    f"Cyware API Error - URL: {url} - Status Code: {response.status_code}, Message: {response.text}"
                )

        except requests.exceptions.Timeout as e:
            raise CTIXTimeoutError(TIMEOUT_MESSAGE) from e
        except requests.exceptions.ConnectionError as e:
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError):
            raise
        except Exception as e:
            logger.error(
                f"Error fetching indicator tags: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error fetching indicator tags: {str(e)}") from e


@Configuration()
class CTIXManageTagsCommand(GeneratingCommand):
    """Command to manage tags for CTIX indicators."""

    ctix_id = Option(require=False, default=None)
    action = Option(require=False, default="add_tags")
    tag_ids = Option(require=False, default="")
    splunk_account = Option(require=False, default=None)

    def _get_friendly_message(self, action):
        """Get user-friendly message based on action."""
        if action == "add_tags":
            return "Tags successfully added to indicator"
        return "Tags successfully removed from indicator"

    def _get_friendly_error(self, error_msg):
        """Convert error message to user-friendly format."""
        if "Credentials missing" in error_msg:
            return "Account credentials not configured. Please check your Splunk account settings."
        if "Cyware ID is required" in error_msg:
            return "Please provide the CTIX Indicator ID."
        if "Tag IDs are required" in error_msg:
            return "Please select at least one tag."
        if "Invalid action" in error_msg:
            return "Invalid action selected. Please choose 'add_tags' or 'remove_tags'."
        return error_msg

    def _build_output(self, action, tag_ids, result):
        """Build output dictionary."""
        output = {
            "action": action,
            "tag_ids": tag_ids,
            "status": "success",
            "message": self._get_friendly_message(action),
            "_time": time.time(),
            "_raw": json.dumps(result)
        }

        if isinstance(result, dict):
            for key, value in result.items():
                if key not in output:
                    output[key] = value

        return output

    def generate(self):
        """Generate CTIX indicator tags."""
        try:
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

            connector = CTIXConnector(api_url, client_id, client_secret, session_key)

            ctix_id = self.ctix_id
            tag_ids = self.tag_ids if self.tag_ids else ""
            action = self.action if self.action else "add_tags"
            logger.info(f"tag_ids: {tag_ids}")

            if not ctix_id:
                raise CTIXValidationError("Cyware ID is required. Please provide the indicator's CTIX ID.")

            if not tag_ids:
                raise CTIXValidationError("Tag IDs are required. Please select at least one tag.")

            logger.info(f"Manage Tags: {action} for indicator ID: {ctix_id}")

            result = connector.manage_tags(
                ctix_id=ctix_id,
                action=action,
                tag_ids=tag_ids
            )

            yield self._build_output(action, tag_ids, result)

        except Exception as err:
            logger.error(f"Manage Tags Error: {str(err)}")
            friendly_error = self._get_friendly_error(str(err))

            yield {
                "action": getattr(self, 'action', 'unknown'),
                "tag_ids": getattr(self, 'tag_ids', ''),
                "status": "error",
                "message": friendly_error,
                "_raw": json.dumps({"error": str(err)}),
                "_time": time.time()
            }
            logger.error(err)


if __name__ == "__main__":
    dispatch(CTIXManageTagsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
