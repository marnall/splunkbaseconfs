"""Get all users from CTIX."""

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


logger = logging_helper.get_logger("get_users")


class CTIXConnector(BaseCTIXConnector):
    """CTIX connector for get users operations."""

    def _estimate_total_pages(self, response, page_size):
        """Estimate total pages from response if available."""
        try:
            response_data = response.json()
            if isinstance(response_data, dict) and 'count' in response_data:
                total_count = response_data['count']
                total_pages = (total_count + page_size - 1) // page_size
                logger.info(f"Estimated total pages: {total_pages}, total users: {total_count}")
                return total_pages
        except Exception as e:
            logger.error(f"Error estimating total pages: {str(e)}")
        return 0

    def _fetch_all_users_pages(self, page_size, is_blocked=False):
        """Fetch all pages of users."""
        all_users = []
        page = 1
        total_pages = 0

        while True:
            logger.debug(f"Fetching page {page} of users")
            response = self._fetch_users_page(page, page_size, is_blocked)
            users, has_next = self._parse_users_response(response)
            all_users.extend(users)

            # Estimate total pages on first iteration if needed
            if total_pages == 0 and has_next:
                total_pages = self._estimate_total_pages(response, page_size)

            logger.info(f"Fetched page {page} with {len(users)} users")

            if not has_next:
                break
            page += 1

        return all_users

    def get_users_list(self, is_blocked=False):
        """Fetch all users from CTIX with pagination support."""
        logger.info("Get users action started")

        try:
            page_size = 100
            logger.info(f"Fetching users with page size: {page_size}, is_blocked: {is_blocked}")

            all_users = self._fetch_all_users_pages(page_size, is_blocked)

            logger.info(f"Successfully fetched all users. Total: {len(all_users)}")
            logger.info(f"Returning {len(all_users)} users to UI")
            return all_users

        except requests.exceptions.Timeout as e:
            logger.error("Request to fetch users timed out")
            raise CTIXTimeoutError(f"Request to CTIX API timed out after {DEFAULT_TIMEOUT} seconds") from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching users: {str(e)}")
            raise CTIXConnectionError(f"Could not connect to CTIX API: {str(e)}") from e
        except (CTIXAPIError, CTIXTimeoutError, CTIXConnectionError):
            raise
        except Exception as e:
            logger.error(
                f"Error fetching users: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error fetching users: {str(e)}") from e

    def _fetch_users_page(self, page, page_size, is_blocked=False):
        """Fetch a single page of users."""
        url = f"{self.api_url}/rest-auth/users/"
        auth_params = self.auth()
        auth_params["page"] = str(page)
        auth_params["page_size"] = str(page_size)
        auth_params["is_blocked"] = "true" if is_blocked else "false"

        headers = {'Content-Type': 'application/json', 'User-Agent': USER_AGENT}

        proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
        ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

        logger.debug(f"Fetching users - Page {page} - URL: {url}")

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

    def _parse_users_response(self, response):
        """Parse users response and return users list and has_next flag."""
        try:
            result = response.json()
            if isinstance(result, dict) and 'results' in result:
                users = result.get('results', [])
                has_next = bool(result.get('next'))
                return users, has_next
            elif isinstance(result, list):
                return result, False
            else:
                return [], False
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing response: {str(e)}")
            return [], False


@Configuration()
class CTIXGetUsersCommand(GeneratingCommand):
    """Command to get all users from CTIX."""

    splunk_account = Option(require=False, default=None)

    def _build_user_output(self, user):
        """Build output dictionary for a single user."""
        return {
            "user_id": user.get("user_id", ""),
            "username": user.get("username", ""),
            "email": user.get("email", ""),
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "is_active": user.get("is_active", True),
            "is_blocked": user.get("is_blocked", False),
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

            logger.info("Intel Exchange: Fetching users list")
            users_list = connector.get_users_list(is_blocked=False)

            logger.info(f"Intel Exchange: Retrieved {len(users_list) if isinstance(users_list, list) else 0} users")

            if not isinstance(users_list, list):
                logger.error(f"Intel Exchange: Unexpected response type: {type(users_list)}")
                yield {
                    "status": "error",
                    "message": "Unexpected response format from CTIX",
                    "_time": time.time()
                }
                return

            if len(users_list) == 0:
                logger.warning("Intel Exchange: No users found")
                yield {
                    "status": "info",
                    "message": "No users found in CTIX",
                    "_time": time.time()
                }
                return

            for user in users_list:
                yield self._build_user_output(user)

        except Exception as err:
            logger.error(f"Get Users Error: {str(err)}")
            yield {
                "status": "error",
                "message": str(err),
                "_raw": json.dumps({"error": str(err)}),
                "_time": time.time()
            }
            logger.error(err)


if __name__ == "__main__":
    dispatch(CTIXGetUsersCommand, sys.argv, sys.stdin, sys.stdout, __name__)
