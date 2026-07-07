"""Get CTIX allowlist indicators."""

import ta_cyware_ctix_declare  # noqa: F401

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
import ta_cyware_ctix.logging_helper as logging_helper
import ta_cyware_ctix.conf_helper as conf_helper
import ta_cyware_ctix.proxy_helper as proxy_helper
import ta_cyware_ctix.ssl_helper as ssl_helper
from ta_cyware_ctix.ctix_exceptions import CTIXConfigurationError
from ta_cyware_ctix.ctix_connector import CTIXConnector as BaseCTIXConnector
from ta_cyware_ctix.constants import DEFAULT_TIMEOUT, USER_AGENT

import sys
import time
import json
import traceback
from ta_cyware_ctix.aob_py3 import requests


logger = logging_helper.get_logger("get_allowlist")


class CTIXConnector(BaseCTIXConnector):
    """CTIX connector for get allowlist operations."""

    def _build_pagination_params(self, page, page_size):
        """Build pagination parameters for API request."""
        params = self.auth()
        params.update({
            "page": page,
            "page_size": page_size,
            "sort": "-created"  # Sort by creation date descending
        })
        return params

    def _fetch_page(self, page, page_size, headers, proxy_config, ssl_verify):
        """Fetch a single page of allowlist data."""
        params = self._build_pagination_params(page, page_size)
        url = f"{self.api_url}/conversion/allowed_indicators/"

        logger.info(f"Fetching page {page} of allowlist (page_size={page_size})")
        logger.debug(f"API parameters: {params}")

        response = requests.get(
            url=url,
            params=params,
            headers=headers,
            proxies=proxy_config,
            verify=ssl_verify,
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()

        return response.json()

    def _extract_records_from_dict(self, data):
        """Extract records from dictionary response."""
        if "results" in data and isinstance(data["results"], list):
            return data["results"], self._check_pagination_from_results(data)

        if "data" in data:
            return self._extract_from_data_field(data["data"])

        return self._extract_from_other_fields(data)

    def _extract_from_data_field(self, data_field):
        """Extract records from the 'data' field of response."""
        if isinstance(data_field, list):
            return data_field, False

        if isinstance(data_field, dict) and isinstance(
            data_field.get("results"), list
        ):
            return data_field["results"], False

        return [], False

    def _extract_from_other_fields(self, data):
        """Extract records from other possible fields in response."""
        records = data.get("allowed_indicators") or data.get("items") or []
        if not isinstance(records, list):
            records = [data]
        return records, False

    def _extract_records_from_response(self, data):
        """Extract records from API response and determine if more pages exist."""
        if isinstance(data, dict):
            return self._extract_records_from_dict(data)
        elif isinstance(data, list):
            return data, False
        else:
            return [], False

    def _check_pagination_from_results(self, data):
        """Check if there are more pages based on response data."""
        if "count" in data:
            # Use total count to determine if more pages exist
            return True  # Let the main loop handle the count comparison
        elif "next" in data:
            # Check if there's a next page URL
            return data["next"] is not None and data["next"] != ""
        return False

    def _should_continue_pagination(self, data, all_records, records, page):
        """Determine if pagination should continue."""
        if not records:
            logger.info(f"No records found on page {page}, stopping pagination")
            return False

        if isinstance(data, dict) and "count" in data:
            total_count = data["count"]
            logger.info(f"Page {page}: Retrieved {len(records)} of {total_count} total records")
            return len(all_records) + len(records) < total_count

        if isinstance(data, dict) and "next" in data:
            return data["next"] is not None and data["next"] != ""

        return False

    def _check_page_limit(self, page):
        """Check if maximum page limit has been reached."""
        if page > 1000:  # Maximum 1000 pages
            logger.warning("Reached maximum page limit (1000), stopping pagination")
            return True
        return False

    def get_allowlist(self, page_size=100):
        """
        Call CTIX conversion allowed indicators API and return all parsed records.

        Args:
            page_size: Number of records to fetch per page (default: 100)

        Returns:
            list: All allowlist records
        """
        logger.info("Get allowlist action started")

        try:
            all_records = []
            page = 1
            headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            while True:
                # Fetch current page
                data = self._fetch_page(page, page_size, headers, proxy_config, ssl_verify)

                # Extract records and check pagination
                records, has_more_from_response = self._extract_records_from_response(data)
                all_records.extend(records)

                # Determine if we should continue
                if not has_more_from_response:
                    if not self._should_continue_pagination(data, all_records, records, page):
                        break

                # Check page limit
                if self._check_page_limit(page):
                    break

                page += 1

            logger.info(f"Successfully fetched {len(all_records)} total allowlist records")
            return all_records

        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to fetch allowlist - HTTP error: {e.response.status_code}")
            raise CTIXConfigurationError(f"Failed to fetch allowlist: {str(e)}") from e
        except requests.exceptions.Timeout as e:
            logger.error("Request to fetch allowlist timed out")
            raise CTIXConfigurationError("Request timed out") from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while fetching allowlist: {str(e)}")
            raise CTIXConfigurationError(f"Connection error: {str(e)}") from e
        except Exception as e:
            logger.error(
                f"Error fetching allowlist: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXConfigurationError(f"Error fetching allowlist: {str(e)}") from e


@Configuration()
class CTIXGetAllowlistCommand(GeneratingCommand):
    """Command to get CTIX allowlist indicators."""

    splunk_account = Option(require=False, default=None)
    page_size = Option(require=False, default="100")

    def _extract_field_value(self, record, *field_names):
        """Extract first non-None value from record using multiple possible field names."""
        for field_name in field_names:
            value = record.get(field_name)
            if value is not None:
                return value
        return None

    def _build_output_record(self, record):
        """Build output record from API response."""
        indicator_id = self._extract_field_value(record, "indicator_id", "id", "object_id")
        indicator_value = self._extract_field_value(record, "indicator_value", "indicator", "value")
        indicator_type = self._extract_field_value(record, "indicator_type", "type", "indicatorType")
        allowlisted_date = self._extract_field_value(
            record, "allowlisted_date", "whitelisted_on", "created_at", "created"
        )
        allowlisted_by = self._extract_field_value(record, "allowlisted_by", "whitelisted_by", "created_by")
        reason = self._extract_field_value(record, "reason", "allowlist_reason", "whitelist_reason")

        return {
            "indicator_id": indicator_id,
            "indicator_value": indicator_value,
            "indicator_type": indicator_type,
            "allowlisted_date": allowlisted_date,
            "allowlisted_by": json.dumps(allowlisted_by) if isinstance(allowlisted_by, dict) else allowlisted_by,
            "reason": reason,
            "_time": time.time(),
            "_raw": json.dumps(record)
        }

    def generate(self):
        """Generate command results."""
        try:
            session_key = self._metadata.searchinfo.session_key
            account_creds = conf_helper.get_account_credentials_for_search_command(
                self.splunk_account, logger, session_key
            )

            api_url = account_creds.get("base_url")
            client_id = account_creds.get("access_id")
            client_secret = account_creds.get("secret_key")

            if not client_id or not client_secret or not api_url:
                raise CTIXConfigurationError("Credentials missing. Please configure account settings.")

            # Validate and parse page_size
            try:
                page_size = int(self.page_size)
                if page_size < 1 or page_size > 1000:
                    logger.warning(f"Invalid page_size {page_size}, using default 100")
                    page_size = 100
            except (ValueError, TypeError):
                logger.warning(f"Invalid page_size '{self.page_size}', using default 100")
                page_size = 100

            connector = CTIXConnector(api_url, client_id, client_secret, session_key)
            records = connector.get_allowlist(page_size=page_size)

            if not records:
                yield {
                    "status": "info",
                    "message": "No allowlisted indicators found for the provided criteria.",
                    "_time": time.time()
                }
                return

            for record in records:
                yield self._build_output_record(record)

        except requests.exceptions.Timeout:
            logger.error(f"Request to CTIX API timed out after {DEFAULT_TIMEOUT} seconds")
            yield {
                "status": "error",
                "message": f"Request to CTIX API timed out after {DEFAULT_TIMEOUT} seconds",
                "_time": time.time()
            }
        except requests.exceptions.RequestException as err:
            logger.error(f"API request failed: {str(err)}")
            yield {
                "status": "error",
                "message": f"Cyware API request failed: {str(err)}",
                "_time": time.time()
            }
        except Exception as err:
            logger.error(f"Error getting allowlist: {str(err)}")
            yield {
                "status": "error",
                "message": str(err),
                "_time": time.time()
            }


if __name__ == "__main__":
    dispatch(CTIXGetAllowlistCommand, sys.argv, sys.stdin, sys.stdout, __name__)
