"""Get tags for CTIX indicators."""

import ta_cyware_ctix_declare  # noqa: F401

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import ta_cyware_ctix.logging_helper as logging_helper
import ta_cyware_ctix.proxy_helper as proxy_helper
import ta_cyware_ctix.ssl_helper as ssl_helper
import ta_cyware_ctix.conf_helper as conf_helper
from ta_cyware_ctix.ctix_exceptions import (
    CTIXAPIError, CTIXConnectionError, CTIXTimeoutError, CTIXConfigurationError
)
from ta_cyware_ctix.ctix_connector import CTIXConnector as BaseCTIXConnector
from ta_cyware_ctix.constants import DEFAULT_TIMEOUT, USER_AGENT

import json
import sys
import time
import traceback
from ta_cyware_ctix.aob_py3 import requests


logger = logging_helper.get_logger("get_indicator_tags")


class CTIXConnector(BaseCTIXConnector):
    """CTIX connector for get indicator tags operations."""

    def get_indicator_tags(self, ctix_id):
        """
        Fetch tags for a specific indicator from CTIX.

        Args:
            ctix_id: CTIX indicator ID (UUID)

        Returns:
            list: List of tags associated with the indicator
        """
        logger.info(f"Get indicator tags action started for ID: {ctix_id}")

        try:
            url = f"{self.api_url}/ingestion/threat-data/indicator/{ctix_id}/basic/"
            auth_params = self.auth()

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': USER_AGENT,
            }

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            logger.info(f"Calling API to fetch tags for indicator: {ctix_id}")
            logger.debug(f"API URL: {url}")

            response = requests.get(
                url=url,
                params=auth_params,
                headers=headers,
                proxies=proxy_config,
                verify=ssl_verify,
                timeout=DEFAULT_TIMEOUT
            )

            if response.ok:
                logger.info(f"Successfully fetched tags for indicator {ctix_id}")
                try:
                    result = response.json()
                    if isinstance(result, dict):
                        tags = result.get('tags', [])
                        logger.info(f"Found {len(tags)} tags for indicator")
                        logger.info(f"Returning {len(tags)} tags to UI")
                        return tags
                    else:
                        logger.warning(f"Unexpected response format for indicator {ctix_id}")
                        return []
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing response: {str(e)}")
                    return []
            else:
                logger.error(f"Failed to fetch tags - Status: {response.status_code}")
                raise CTIXAPIError(
                    f"API Error - URL: {url} - Status Code: {response.status_code}, Message: {response.text}"
                )

        except requests.exceptions.Timeout as e:
            raise CTIXTimeoutError(f"Request to CTIX API timed out after {DEFAULT_TIMEOUT} seconds") from e
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
class CTIXGetIndicatorTagsCommand(GeneratingCommand):
    """Command to get tags for CTIX indicators."""

    ctix_id = Option(require=False, default=None)
    splunk_account = Option(require=False, default=None)

    def generate(self):
        """Generate command results."""
        try:
            if not self.ctix_id:
                logger.error("Indicator ID is required")
                yield {
                    "status": "error",
                    "message": "Cyware Indicator ID is required",
                    "_time": time.time()
                }
                return

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

            logger.info(f"Intel Exchange: Fetching tags for indicator: {self.ctix_id}")
            tags_list = connector.get_indicator_tags(self.ctix_id)

            if isinstance(tags_list, list) and len(tags_list) > 0:
                for tag in tags_list:
                    yield {
                        "id": tag.get("id", ""),
                        "name": tag.get("name", ""),
                        "colour_code": tag.get("colour_code", ""),
                        "tag_type": tag.get("tag_type", ""),
                        "theme": tag.get("theme", ""),
                        "_time": time.time()
                    }
            elif isinstance(tags_list, list) and len(tags_list) == 0:
                yield {
                    "status": "info",
                    "message": "No tags found for this indicator",
                    "_time": time.time()
                }
            else:
                yield {
                    "status": "error",
                    "message": "Unexpected response format from CTIX",
                    "_time": time.time()
                }

        except Exception as err:
            logger.error(f"Get Indicator Tags Error: {str(err)}")
            yield {
                "status": "error",
                "message": str(err),
                "_raw": json.dumps({"error": str(err)}),
                "_time": time.time()
            }
            logger.error(err)


if __name__ == "__main__":
    dispatch(CTIXGetIndicatorTagsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
