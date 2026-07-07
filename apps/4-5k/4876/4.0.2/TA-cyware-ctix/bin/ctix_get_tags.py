"""Get all tags from CTIX."""

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


logger = logging_helper.get_logger("get_tags")


class CTIXConnector(BaseCTIXConnector):
    """CTIX connector for get tags operations."""

    def _estimate_total_pages(self, response, page_size):
        """Estimate total pages from response if available."""
        try:
            response_data = response.json()
            if isinstance(response_data, dict) and 'count' in response_data:
                total_count = response_data['count']
                total_pages = (total_count + page_size - 1) // page_size
                logger.info(f"Estimated total pages: {total_pages}, total tags: {total_count}")
                return total_pages
        except Exception as e:
            logger.error(f"Error estimating total pages: {str(e)}")
        return 0

    def _fetch_all_tags_pages(self, page_size):
        """Fetch all pages of tags."""
        all_tags = []
        page = 1
        total_pages = 0

        while True:
            logger.debug(f"Fetching page {page} of tags")
            response = self._fetch_tags_page(page, page_size)
            tags, has_next = self._parse_tags_response(response)
            all_tags.extend(tags)

            # Estimate total pages on first iteration if needed
            if total_pages == 0 and has_next:
                total_pages = self._estimate_total_pages(response, page_size)

            logger.info(f"Fetched page {page} with {len(tags)} tags")

            if not has_next:
                break
            page += 1

        return all_tags

    def get_tags_list(self):
        """Fetch all tags from CTIX with pagination support."""
        logger.info("Get tags action started")

        try:
            page_size = 100
            logger.info(f"Fetching tags with page size: {page_size}")

            all_tags = self._fetch_all_tags_pages(page_size)

            logger.info(f"Successfully fetched all tags. Total: {len(all_tags)}")
            logger.info(f"Returning {len(all_tags)} tags to UI")
            return all_tags

        except requests.exceptions.Timeout as e:
            logger.error("Request to fetch tags timed out")
            raise CTIXTimeoutError(f"Request to CTIX API timed out after {DEFAULT_TIMEOUT} seconds") from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching tags: {str(e)}")
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError):
            raise
        except Exception as e:
            logger.error(
                f"Error fetching tags: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error fetching tags: {str(e)}") from e

    def _fetch_tags_page(self, page, page_size):
        """Fetch a single page of tags."""
        url = f"{self.api_url}/ingestion/tags/"
        auth_params = self.auth()
        auth_params["page"] = str(page)
        auth_params["page_size"] = str(page_size)

        headers = {'Content-Type': 'application/json', 'User-Agent': USER_AGENT}

        proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
        ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

        logger.debug(f"Fetching tags - Page {page} - URL: {url}")

        response = requests.get(
            url=url,
            params=auth_params,
            headers=headers,
            proxies=proxy_config,
            verify=ssl_verify,
            timeout=DEFAULT_TIMEOUT
        )

        if not response.ok:
            raise CTIXAPIError(
                f"Cyware API Error - URL: {url} - Status Code: {response.status_code}, Message: {response.text}"
            )

        return response

    def _parse_tags_response(self, response):
        """Parse tags response and return tags list and has_next flag."""
        try:
            result = response.json()
            if isinstance(result, dict) and 'results' in result:
                tags = result.get('results', [])
                has_next = bool(result.get('next'))
                return tags, has_next
            elif isinstance(result, list):
                return result, False
            else:
                return [], False
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing response: {str(e)}")
            return [], False


@Configuration()
class CTIXGetTagsCommand(GeneratingCommand):
    """Command to get all tags from CTIX."""

    splunk_account = Option(require=False, default=None)

    def _build_tag_output(self, tag):
        """Build output dictionary for a single tag."""
        tag_type = ""
        if isinstance(tag.get("tag_type"), dict):
            tag_type = tag.get("tag_type", {}).get("name", "")

        return {
            "id": tag.get("id", ""),
            "name": tag.get("name", ""),
            "colour_code": tag.get("colour_code", ""),
            "tag_type": tag_type,
            "is_active": tag.get("is_active", True),
            "_time": time.time()
        }

    def generate(self):
        """Generate command results."""
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

            logger.info("Intel Exchange: Fetching tags list")
            tags_list = connector.get_tags_list()

            logger.info(f"Intel Exchange: Retrieved {len(tags_list) if isinstance(tags_list, list) else 0} tags")

            if not isinstance(tags_list, list):
                logger.error(f"Intel Exchange: Unexpected response type: {type(tags_list)}")
                yield {
                    "status": "error",
                    "message": "Unexpected response format from CTIX",
                    "_time": time.time()
                }
                return

            if len(tags_list) == 0:
                logger.warning("Intel Exchange: No tags found")
                yield {
                    "status": "info",
                    "message": "No tags found in CTIX",
                    "_time": time.time()
                }
                return

            for tag in tags_list:
                yield self._build_tag_output(tag)

        except Exception as err:
            logger.error(f"Get Tags Error: {str(err)}")
            yield {
                "status": "error",
                "message": str(err),
                "_raw": json.dumps({"error": str(err)}),
                "_time": time.time()
            }
            logger.error(err)


if __name__ == "__main__":
    dispatch(CTIXGetTagsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
