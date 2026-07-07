"""This module provides functionality to add indicators to CTIX via the workflow actions in Splunk."""
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
from ta_cyware_ctix.constants import DEFAULT_TIMEOUT, INDICATOR_TYPE_MAPPING, VALID_INDICATOR_TYPES, USER_AGENT

import json
import sys
import time
import traceback
from ta_cyware_ctix.aob_py3 import requests


logger = logging_helper.get_logger("add_indicator")


# -----------------------------
# CTIX Connector
# -----------------------------
class CTIXConnector(BaseCTIXConnector):
    """CTIX connector for add indicator operations."""

    def add_indicator(self, indicator_type, value, title, description, confidence, tlp, tags, valid_until, apply_all):
        """
        Add indicator to CTIX using quick intel creation endpoint.

        Args:
            indicator_type: Type of indicator (user-friendly name or backend value)
            value: Indicator value
            title: Title for the indicator
            description: Description for the indicator
            tlp: TLP marking (CLEAR, GREEN, AMBER, AMBER_STRICT, RED)
            confidence: Confidence score (0-100)
            tags: Comma-separated list of tags
            apply_all: Whether to apply metadata to all objects

        Returns:
            dict: API response
        """
        logger.info(f"Add indicator action started for {indicator_type}: {value}")

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

            url = f"{self.api_url}/conversion/quick-intel/create-stix/"
            auth_params = self.auth()

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': USER_AGENT,
            }

            # Prepare tags list
            tags_list = []
            if tags:
                tags_list = [t.strip() for t in tags.split(",") if t.strip()]
            tags_list.append("created_from_splunk")

            # Build metadata (matching CTIX API structure)
            metadata = {
                "tlp": tlp or "AMBER",
                "default_marking_definition": tlp or "AMBER",
                "marking_config": "tlp2",
                "tags": tags_list,
                "is_apply_all": str(apply_all).lower() in ["true", "yes", "1"],
                "additional_defaults": [],
                "custom_scores": {},
                "confidence": int(confidence) if confidence else 100,
                "valid_until": valid_until
            }

            # Build the payload
            payload = {
                "context": "QUICK_ADD_INTEL_FLOW",
                "parsed_indicators": {},
                "metadata": metadata,
                "indicators": {
                    mapped_type: value
                },
                "title": title or "Added from Splunk",
                "relations": [],
                "create_intel_feed": True,
                "valid_until": valid_until
            }

            # Add description if provided
            if description:
                payload["description"] = description

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            # Make the API request
            logger.info(f"Calling API to add indicator: {url}")
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
                logger.info(f"Successfully added indicator {mapped_type}: {value}")
                try:
                    result = response.json()
                    return result
                except json.JSONDecodeError:
                    return {
                        "status": "success",
                        "message": "Indicator added successfully",
                        "response_text": response.text
                    }
            else:
                logger.error(f"Failed to add indicator - Status: {response.status_code}")
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
                f"Error adding indicator to Cyware Intel Exchange: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error adding indicator to Cyware Intel Exchange: {str(e)}") from e


# -----------------------------
# Splunk Generating Command
# -----------------------------
@Configuration()
class CTIXAddIndicatorCommand(GeneratingCommand):
    """Generating command class for adding an indicator to CTIX."""

    indicator_type = Option(require=False, default="ipv4-addr")
    value = Option(require=False, default=None)
    title = Option(require=False, default="Added from Splunk")
    description = Option(require=False, default="")
    confidence = Option(require=False, default="100")
    tlp = Option(require=False, default="AMBER")
    tags = Option(require=False, default="")
    valid_until = Option(require=False, default="")
    apply_all = Option(require=False, default="true")
    splunk_account = Option(require=False, default=None)

    def generate(self):
        """Generate results for the CTIX Add Indicator Splunk command."""
        try:
            # ===== Get Configuration =====
            # Multi-account: Get credentials for the specified account via REST call
            session_key = self._metadata.searchinfo.session_key
            account_creds = conf_helper.get_account_credentials_for_search_command(
                self.splunk_account, logger, session_key
            )
            logger.debug(f"Successfully fetched credentials for account: {self.splunk_account}")
            api_url = account_creds.get("base_url")
            client_id = account_creds.get("access_id")
            client_secret = account_creds.get("secret_key")

            if not client_id or not client_secret or not api_url:
                raise CTIXConfigurationError(
                    "Credentials missing. Please configure base_url, access_id, and secret_key "
                    "in Add-on Settings or select a valid account."
                )

            # ===== Validate Input Parameters =====
            if not self.value:
                raise CTIXValidationError("Indicator value is required. Please provide a value.")

            # Clean up the API URL
            api_url = api_url.rstrip('/')

            # ===== Log Operation =====
            logger.info(f"Adding indicator to Intel Exchange: type={self.indicator_type}, value={self.value}")

            # ===== Call CTIX API =====
            result = CTIXConnector(api_url, client_id, client_secret, session_key).add_indicator(
                indicator_type=self.indicator_type,
                value=self.value,
                title=self.title,
                description=self.description,
                confidence=self.confidence,
                tlp=self.tlp,
                tags=self.tags,
                valid_until=self.valid_until,
                apply_all=self.apply_all
            )

            logger.info(f"Successfully added indicator. Response: {json.dumps(result)[:200]}")

            # Get the mapped type for output
            mapped_type = INDICATOR_TYPE_MAPPING.get(self.indicator_type, self.indicator_type)

            output = {
                "indicator_type": self.indicator_type,
                "indicator_type_backend": mapped_type,
                "value": self.value,
                "title": self.title,
                "tlp": self.tlp,
                "confidence": self.confidence,
                "tags": self.tags,
                "valid_until": self.valid_until,
                "status": "Success",
                "message": "Indicator adding request is successful to Cyware",
                "_time": time.time(),
                "_raw": json.dumps(result)
            }

            # Add API response details if available
            if isinstance(result, dict):
                # Extract useful fields from the response
                if "id" in result:
                    output["ctix_id"] = result["id"]
                if "created" in result:
                    output["created_time"] = result["created"]
                if "object_id" in result:
                    output["object_id"] = result["object_id"]

                # Add full response
                output["api_response"] = json.dumps(result)

            yield output

        except Exception as err:
            logger.error(f"Error adding indicator to Intel Exchange: {str(err)}")

            yield {
                "indicator_type": getattr(self, 'indicator_type', 'unknown'),
                "value": getattr(self, 'value', 'unknown'),
                "title": getattr(self, 'title', ''),
                "status": "error",
                "message": str(err),
                "_raw": json.dumps({"error": str(err)}),
                "_time": time.time()
            }

            logger.error(err)


if __name__ == "__main__":
    dispatch(CTIXAddIndicatorCommand, sys.argv, sys.stdin, sys.stdout, __name__)
