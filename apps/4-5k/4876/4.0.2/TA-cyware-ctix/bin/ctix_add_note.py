"""Add notes to CTIX indicators."""

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


logger = logging_helper.get_logger("add_note")


class CTIXConnector(BaseCTIXConnector):
    """CTIX connector for add note operations."""

    def add_note(self, ctix_id, note_content, note_type="threatdata"):
        """
        Add a note to an indicator in CTIX.

        Args:
            ctix_id: CTIX indicator ID (UUID)
            note_content: Note content/description text
            note_type: Type of note (default: "threatdata" for threat data/indicators)

        Returns:
            dict: API response
        """
        logger.info(f"Add note action started for indicator ID: {ctix_id}")

        try:
            url = f"{self.api_url}/ingestion/notes/"
            auth_params = self.auth()

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': USER_AGENT,
            }

            payload = {
                "object_id": ctix_id,
                "text": note_content,
                "type": note_type
            }

            proxy_config = proxy_helper.get_proxy_config(self.session_key, logger)
            ssl_verify = ssl_helper.get_ssl_verify(self.session_key, logger)

            logger.info(f"Calling API to add note to indicator: {ctix_id}")
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
                logger.info(f"Successfully added note to indicator {ctix_id}")
                try:
                    result = response.json()
                    return result
                except json.JSONDecodeError:
                    return {"status": "success", "message": response.text}
            else:
                logger.error(f"Failed to add note - Status: {response.status_code}")
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
                f"Error adding note: {str(e)}\n{traceback.format_exc()}"
            )
            raise CTIXAPIError(f"Error adding note: {str(e)}") from e


@Configuration()
class CTIXAddNoteCommand(GeneratingCommand):
    """Command to add notes to CTIX indicators."""

    ctix_id = Option(require=False, default=None)
    note_content = Option(require=False, default="")
    splunk_account = Option(require=False, default=None)

    def _get_friendly_error(self, error_msg):
        """Convert error message to user-friendly format."""
        if "Credentials missing" in error_msg:
            return "Account credentials not configured. Please check your Splunk account settings."
        if "Cyware ID is required" in error_msg:
            return "Please provide the CTIX Indicator ID."
        if "Note content is required" in error_msg:
            return "Please provide note content."
        return error_msg

    def _build_output(self, note_content, result):
        """Build output dictionary."""
        output = {
            "note_content": note_content,
            "status": "success",
            "message": "Note successfully added to indicator",
            "_time": time.time(),
            "_raw": json.dumps(result)
        }

        if isinstance(result, dict):
            for key, value in result.items():
                if key not in output and key not in ['indicator_id', 'note_id']:
                    output[key] = value

        return output

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

            ctix_id = self.ctix_id
            note_content = self.note_content if self.note_content else ""

            if not ctix_id:
                raise CTIXValidationError("Cyware ID is required. Please provide the indicator's CTIX ID.")

            if not note_content:
                raise CTIXValidationError("Note content is required. Please provide note text.")

            logger.info(f"Add Note: Adding note to indicator ID: {ctix_id}")

            result = CTIXConnector(api_url, client_id, client_secret, session_key).add_note(
                ctix_id=ctix_id,
                note_content=note_content
            )

            yield self._build_output(note_content, result)

        except Exception as err:
            logger.error(f"Add Note Error: {str(err)}")
            friendly_error = self._get_friendly_error(str(err))

            yield {
                "note_content": getattr(self, 'note_content', ''),
                "status": "error",
                "message": friendly_error,
                "_raw": json.dumps({"error": str(err)}),
                "_time": time.time()
            }
            logger.error(err)


if __name__ == "__main__":
    dispatch(CTIXAddNoteCommand, sys.argv, sys.stdin, sys.stdout, __name__)
