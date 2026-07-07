# -----------------------------------------------
# FeedbackExport Custom Splunk Command
# -----------------------------------------------
# This script defines a Splunk custom streaming command to:
# 1. Collect incoming events with feedback.
# 2. Convert events into JSON format.
# 3. Compress the JSON data into an in-memory ZIP file.
# 4. Upload the ZIP file to a remote REST endpoint.
# -----------------------------------------------

from __future__ import absolute_import, print_function

import base64
import requests
import io
import json
import os
import subprocess
import tempfile
import zipfile
from typing import Dict, Optional, List, Union

from splunklib.searchcommands import (
    StreamingCommand,
    Configuration,
    Option,
    dispatch,
)

import logging
import time
import sys

# -----------------------------------------------
# Global Configuration and Logger Initialization
# -----------------------------------------------

_SPLUNK_HOME = os.environ.get("SPLUNK_HOME", "/opt/splunk")
_LOG_PATH = os.path.join(_SPLUNK_HOME, "var", "log", "splunk", "feedbackexport.log")

# Initialize a logger for the FeedbackExport command
_LOGGER = logging.getLogger("feedbackexport")
_LOGGER.setLevel(logging.WARNING)

if not _LOGGER.handlers:  # Ensure no duplicate handlers are added
    _fh = logging.FileHandler(_LOG_PATH)
    _formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    # Force UTC instead of local time
    _formatter.converter = time.gmtime
    _fh.setFormatter(_formatter)
    _LOGGER.addHandler(_fh)

    # Only send warnings/errors to Splunk UI
    _sh = logging.StreamHandler(sys.stderr)
    _sh.setLevel(logging.WARNING)
    _sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    _LOGGER.addHandler(_sh)

    _LOGGER.propagate = False  # Prevent log propagation to Splunk's main logs

_LOGGER.debug("[INIT] Logger initialized for the FeedbackExport script.")


# -----------------------------------------------
# Helper Functions
# -----------------------------------------------
def _http_get_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    local_verify: Union[str, bool] = True,
) -> Dict:
    """
    Sends an HTTPS GET request to a given URL and parses the JSON response.

    Args:
        url (str): Target URL for the GET request.
        headers (Optional[Dict[str, str]]): HTTP headers to include in the request (default: None).
        local_verify (str | bool): How to call requests verify. Can be True (default) False or a string with the path to the CA file.

    Returns:
        Dict: Parsed JSON response.

    Raises:
        HTTPError: If the response status is not 2xx.
        RequestException: For other request-related errors.
        JSONDecodeError: If the response body is not valid JSON.
        Exception: For unexpected errors.
    """
    _LOGGER.debug("[HTTP GET] Initiating GET request.")

    try:
        response = requests.get(url, headers=headers or {}, verify=local_verify)
        response.raise_for_status()
        _LOGGER.debug("[HTTP GET] HTTP Status: %d", response.status_code)
        return response.json()
    except requests.exceptions.HTTPError as err:
        _LOGGER.error(
            "[HTTP ERROR] %s – %s", err.response.status_code, err.response.reason
        )
        raise
    except requests.exceptions.RequestException as err:
        _LOGGER.error("[REQUEST ERROR] Failed: %s", err)
        raise
    except json.JSONDecodeError as err:
        _LOGGER.error("[JSON ERROR] Invalid JSON: %s", err)
        raise
    except Exception as err:
        _LOGGER.exception("[EXCEPTION] Unexpected error in _http_get_json: %s", err)
        raise


def _encrypt_password(
    clear_pass: str,
    base_url: str,
) -> str:
    """
    Fetch RSA public key from the server and encrypt *clear_pass* with openssl.
    """
    _LOGGER.debug("[ENCRYPTION] Fetching public key and encrypting password.")

    key_url = base_url.rstrip("/") + "/upload/client-encrypt-key"
    headers = {"X-SPLUNK-UPLOAD": "splunk-app-scma"}

    try:
        # Fetch the RSA public key from the server.
        info = _http_get_json(key_url, headers=headers)
        if info.get("status_code") != 200:
            _LOGGER.error(
                "[ENCRYPTION ERROR] Unable to retrieve public key. Server responded with status code '%s'.",
                info.get("status_code"),
            )
            raise RuntimeError("Failed to retrieve public key for encryption.")

        pub_pem = info["data"]["publicKey"].encode()
        _LOGGER.debug("[ENCRYPTION] Successfully retrieved public key from server.")

        # Write public key to a temporary file for openssl
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(pub_pem)
            pub_path = tf.name

        # Use openssl to encrypt the password
        res = subprocess.run(
            ["openssl", "rsautl", "-encrypt", "-pubin", "-inkey", pub_path],
            input=clear_pass.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        os.remove(pub_path)

        # Return the base64-encoded encrypted password
        return base64.b64encode(res.stdout).decode()
    except Exception as exc:
        _LOGGER.error(
            "[ENCRYPTION FAILED] Unable to encrypt password. Falling back to clear password over TLS. Error: %s",
            str(exc),
        )
        return clear_pass


def _upload_file(
    file_bytes: bytes,
    filename: str,
    base_url: str,
    username: str,
    password: str,
) -> bool:
    """
    POST *file_bytes* to /upload/types using multipart/form‑data.
    """
    _LOGGER.debug("[UPLOAD] Starting file upload process.")

    # Construct the URL
    url = base_url.rstrip("/") + "/upload/types/insightsuite"

    # Construct headers
    auth_token = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_token}",
        "X-SPLUNK-UPLOAD": "splunk-app-scma",
    }

    files = {"upload": (filename, file_bytes, "application/zip")}

    try:
        _LOGGER.debug("[UPLOAD] Initiating file upload to endpoint")
        response = requests.post(url, files=files, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad status codes

        # Parse the response JSON
        data = response.json()
        if data.get("status_code") != 200:
            _LOGGER.error(
                "[UPLOAD ERROR] Failed with status code %s and message: %s",
                data.get("status_code"),
                data.get("msg"),
            )
            return False

        # Extract the Salesforce ID (sfdc_id) and the file name from the file destination string,
        # which is returned by the upload service.
        file_destination = data.get("data", {}).get("fileDestination", "")
        parts = file_destination.split("-USER-", 1)
        if len(parts) > 1:
            after = parts[1]
            sfdc_id = after.split("-", 1)[0]
            idx = after.find("-")
            file_name = after[idx + 1 :] if idx != -1 else after
        else:
            sfdc_id = None
            file_name = None

        download_url = f"https://downloadsvc.splunk.com/download/{file_destination}"
        _LOGGER.debug(
            "[UPLOAD SUCCESS] File '%s' uploaded. Download URL: '%s'",
            file_name,
            download_url,
        )

        return True

    except requests.exceptions.HTTPError as errh:
        _LOGGER.error("[HTTP ERROR] %s", errh)
    except requests.exceptions.ConnectionError as errc:
        _LOGGER.error("[CONNECTION ERROR] %s", errc)
    except requests.exceptions.Timeout as errt:
        _LOGGER.error("[TIMEOUT ERROR] %s", errt)
    except requests.exceptions.RequestException as err:
        _LOGGER.error("[REQUEST ERROR] %s", err)
    except Exception as e:
        _LOGGER.exception("[EXCEPTION] Unexpected error during file upload: %s", e)

    return False


def _read_password(
    username: str,
    realm: str = "is4s_data_export",
    base_url: str = "https://localhost:8089",
    session_key: str = "",
    local_verify: Union[str, bool] = True,
) -> str:
    """
    Retrieves the password for the given username and realm from Splunk's storage/passwords endpoint.
    Uses session_key for authentication instead of a password. If the password entry does not exist or an error occurs, returns an empty string.
    """
    _LOGGER.debug(
        "[PASSWORD RETRIEVAL] Starting password retrieval for username '%s'.", username
    )

    # Construct the URL for Splunk's REST API
    url = f"{base_url}/servicesNS/nobody/splunk_insights/storage/passwords/{realm}:{username}?output_mode=json"

    # Headers for authentication using session_key
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {session_key}",
    }

    try:
        _LOGGER.debug(
            "[PASSWORD RETRIEVAL] Sending GET request to Splunk storage/passwords endpoint. Username: '%s', Realm: '%s'",
            username,
            realm,
        )

        # Send the GET request
        response = requests.get(url, headers=headers, verify=local_verify)
        response.raise_for_status()

        # Parse the response JSON
        data = response.json()
        if "entry" not in data or not data["entry"]:
            _LOGGER.warning(
                "[PASSWORD RETRIEVAL WARNING] Password entry not found for username '%s' in realm '%s'. Returning empty string.",
                username,
                realm,
            )
            return ""

        # Extract the clear password from the response
        password = data["entry"][0]["content"]["clear_password"]
        _LOGGER.debug(
            "[PASSWORD RETRIEVAL] Successfully retrieved password for username '%s' in realm '%s'.",
            username,
            realm,
        )
        return password

    except requests.exceptions.HTTPError as errh:
        if errh.response.status_code == 404:
            _LOGGER.warning(
                "[PASSWORD RETRIEVAL WARNING] Password entry not found for username '%s' in realm '%s'. Returning empty string.",
                username,
                realm,
            )
            return ""
        else:
            _LOGGER.error(
                "[PASSWORD RETRIEVAL ERROR] HTTP error while retrieving password for '%s' in realm '%s': %s",
                username,
                realm,
                errh,
            )
    except Exception as exc:
        _LOGGER.exception(
            "[EXCEPTION] Unexpected error during password retrieval: %s", exc
        )

    # Default fallback: Return an empty string if anything goes wrong
    _LOGGER.warning(
        "[PASSWORD RETRIEVAL] No password found for username '%s' in realm '%s'. Returning empty string.",
        username,
        realm,
    )
    return ""


def _get_user(
    base_url: str,
    session_key: str,
    current_username: str,
    local_verify: Union[str, bool],
) -> Optional[str]:
    """
    Fetches the stored username from Splunk's storage/passwords endpoint and compares it with the current username.

    Args:
        base_url (str): Base URL of the Splunk REST API.
        session_key (str): Splunk session key for authentication.
        current_username (str): The current username to compare against.
        local_verify: Verify setting to pass to requests

    Returns:
        Optional[str]: A user message or None if the usernames match.
    """
    url = f"{base_url}/servicesNS/nobody/splunk_insights/storage/passwords?output_mode=json"

    headers = {
        "Authorization": f"Bearer {session_key}",
        "Content-Type": "application/json",
    }

    try:
        _LOGGER.debug("[USER FETCH] Sending GET request to retrieve user.")
        response = requests.get(url, headers=headers, verify=local_verify)

        if response.status_code == 200:
            data = response.json()
            if "entry" in data and data["entry"]:
                entry = next((e for e in data["entry"] if e["content"].get("realm") == "is4s_data_export"), None)

                if entry:
                    stored_username = str(entry["content"]["username"]).replace('"', "")

                    if stored_username == current_username:
                        _LOGGER.debug(
                            "[USER FETCH] Current username matches stored username: %s",
                            stored_username,
                        )
                        return None
                    else:
                        _LOGGER.debug(
                            "[USER FETCH] Current username does not match stored username: %s",
                            stored_username,
                        )
                        return f"The current configured user is: {stored_username}"
                else:
                    _LOGGER.warning("[USER FETCH] No user found for realm 'is4s_data_export'.")
                    return None
            else:
                _LOGGER.warning("[USER FETCH] No user data found in the response.")
                return None
        else:
            _LOGGER.error(
                "[USER FETCH ERROR] Failed to retrieve user. HTTP Status: %d",
                response.status_code,
            )
            return None
    except Exception as e:
        _LOGGER.exception(
            "[USER FETCH ERROR] An error occurred while fetching user details: %s",
            str(e),
        )
        return None


def _get_customer_name(
    base_url: str, session_key: str, local_verify: Union[str, bool] = True
) -> Optional[str]:
    """
    Fetches the customer name from the Splunk REST API.

    Args:
        base_url (str): Base URL of the Splunk REST API.
        session_key (str): Splunk session key for authentication.
        local_verify: Verify setting to pass to requests

    Returns:
        Optional[str]: The customer name if successfully retrieved, otherwise None.
    """
    url = f"{base_url}/servicesNS/-/splunk_insights/configs/conf-macros/ssef_customer_name?output_mode=json"

    headers = {"Authorization": f"Bearer {session_key}"}

    try:
        response = requests.get(url, headers=headers, verify=local_verify)

        if 200 <= response.status_code <= 299:
            data = response.json()
            customer_name = str(data["entry"][0]["content"]["definition"])
            customer_name = customer_name.replace('"', "")
            return customer_name
        else:
            _LOGGER.error(
                "[CUSTOMER NAME] Could not retrieve customer name. HTTP Status: %d",
                response.status_code,
            )
            return None
    except Exception as e:
        _LOGGER.exception(
            "[CUSTOMER NAME ERROR] An error occurred while fetching the customer name: %s",
            str(e),
        )
        return None


def _run_feedback_search(
    base_url: str,
    session_key: str,
    earliest_time: str = "-24h",
    latest_time: str = "now",
    local_verify: Union[str, bool] = True,
) -> List[Dict]:
    """
    Runs the feedback search query and returns the results.

    Args:
        base_url (str): Base URL of the Splunk REST API.
        session_key (str): Splunk session key for authentication.
        earliest_time (str): Earliest time for the search (default: "-24h").
        latest_time (str): Latest time for the search (default: "now").
        local_verify: Verify setting to pass to requests.

    Returns:
        List[Dict]: List of feedback events.
    """
    _LOGGER.debug("[FEEDBACK SEARCH] Starting feedback search.")

    # Create a search job
    search_url = f"{base_url}/services/search/jobs"
    headers = {
        "Authorization": f"Bearer {session_key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # The feedback search query
    search_query = '`ssef_summary_index` source="splunk_insights:feedback" | eval customer_name=`ssef_customer_name`'

    data = {
        "search": f"search {search_query}",
        "earliest_time": earliest_time,
        "latest_time": latest_time,
        "output_mode": "json",
    }

    try:
        # Create the search job
        _LOGGER.debug("[FEEDBACK SEARCH] Creating search job.")
        response = requests.post(search_url, headers=headers, data=data, verify=local_verify)
        response.raise_for_status()

        job_data = response.json()
        sid = job_data.get("sid")
        if not sid:
            _LOGGER.error("[FEEDBACK SEARCH] Failed to get search job SID.")
            return []

        _LOGGER.debug("[FEEDBACK SEARCH] Search job created with SID: %s", sid)

        # Wait for the search job to complete
        job_status_url = f"{base_url}/services/search/jobs/{sid}?output_mode=json"
        max_wait = 300  # Maximum wait time in seconds
        wait_interval = 2  # Check every 2 seconds
        elapsed = 0

        while elapsed < max_wait:
            status_response = requests.get(job_status_url, headers=headers, verify=local_verify)
            status_response.raise_for_status()
            status_data = status_response.json()

            dispatch_state = status_data.get("entry", [{}])[0].get("content", {}).get("dispatchState", "")
            if dispatch_state == "DONE":
                _LOGGER.debug("[FEEDBACK SEARCH] Search job completed.")
                break
            elif dispatch_state == "FAILED":
                _LOGGER.error("[FEEDBACK SEARCH] Search job failed.")
                return []

            time.sleep(wait_interval)
            elapsed += wait_interval

        if elapsed >= max_wait:
            _LOGGER.error("[FEEDBACK SEARCH] Search job timed out.")
            return []

        # Get the results
        results_url = f"{base_url}/services/search/jobs/{sid}/results?output_mode=json&count=0"
        results_response = requests.get(results_url, headers=headers, verify=local_verify)
        results_response.raise_for_status()

        results_data = results_response.json()
        feedback_results = results_data.get("results", [])

        _LOGGER.debug("[FEEDBACK SEARCH] Retrieved %d feedback events.", len(feedback_results))
        return feedback_results

    except requests.exceptions.HTTPError as errh:
        _LOGGER.error("[FEEDBACK SEARCH] HTTP error: %s", errh)
    except requests.exceptions.RequestException as err:
        _LOGGER.error("[FEEDBACK SEARCH] Request error: %s", err)
    except Exception as e:
        _LOGGER.exception("[FEEDBACK SEARCH] Unexpected error: %s", str(e))

    return []


# -----------------------------------------------------------------------------
# Splunk Search Command definition
# -----------------------------------------------------------------------------
_LOGGER.debug("[CONFIGURATION] Initializing Splunk command configuration.")


@Configuration(
    local=True,  # one interpreter, on the search-head
)
class FeedbackExport(StreamingCommand):
    """
    Splunk Custom Streaming Command: FeedbackExport

    This command performs the following steps:
    1. Collects incoming events from the Splunk pipeline with feedback.
    2. Converts the events into JSON format.
    3. Compresses the JSON data into a ZIP archive.
    4. Uploads the ZIP file to a specified remote REST API endpoint.

    Configuration:
    - Local execution only (`local=True`).
    - Optional options: `username`, `customer_name`.
    """

    # Hardcode the target URL
    target_url = "https://uploadsvc.splunk.com/api/v2"

    username = Option(require=False)
    customer_name = Option(require=False)
    insecure = Option(require=False, default="true")
    local_verify = Option(require=False, default="true")

    def __init__(self):

        _LOGGER.debug("[INIT] FeedbackExport command instance created.")

        super(FeedbackExport, self).__init__()
        self._events: List[Dict] = []  # acccumulate events for JSON serialisation

    # This method processes incoming records with feedback, retrieves credentials, compresses the events into a ZIP file,
    # and uploads the file to the specified REST API endpoint.
    def stream(self, records):

        _LOGGER.debug("[STREAM] Starting FeedbackExport command.")

        if hasattr(self.local_verify, "lower") and self.local_verify.lower() == "true":
            self.verify = True
        elif (
            hasattr(self.local_verify, "lower") and self.local_verify.lower() == "false"
        ):
            self.verify = False

        try:
            # Initialize variables
            session_key = None
            username = None
            splunkd_uri = None
            base_url = os.environ.get("SPLUNK_BASE_URL", "https://localhost:8089")

            # Check if searchinfo is accessible as an object or dictionary
            if hasattr(self.metadata, "searchinfo"):
                searchinfo = self.metadata.searchinfo

                # Retrieve session_key
                if hasattr(searchinfo, "session_key"):  # Access as an attribute
                    session_key = searchinfo.session_key
                elif isinstance(searchinfo, dict):  # Access as a dictionary
                    session_key = searchinfo.get("session_key", None)

                # Retrieve username
                if hasattr(searchinfo, "username"):  # Access as an attribute
                    username = searchinfo.username
                elif isinstance(searchinfo, dict):  # Access as a dictionary
                    username = searchinfo.get("username", None)

                # Retrieve splunkd_uri
                if hasattr(searchinfo, "splunkd_uri"):  # Access as an attribute
                    splunkd_uri = searchinfo.splunkd_uri
                elif isinstance(searchinfo, dict):  # Access as a dictionary
                    splunkd_uri = searchinfo.get("splunkd_uri", None)

            # Fallback to environment variables for required fields
            if not session_key:
                _LOGGER.warning(
                    "[SESSION KEY WARNING] Session key not found in metadata. Attempting to retrieve from environment."
                )
                session_key = os.environ.get(
                    "SPLUNK_SESSION_KEY"
                )  # Fallback to environment variable
            if not session_key:
                _LOGGER.critical(
                    "[SESSION KEY ERROR] Session key is required but missing."
                )
                raise RuntimeError("Session key is required but missing.")

            if not username:
                _LOGGER.warning(
                    "[USERNAME WARNING] Username not found in metadata. Attempting to retrieve from environment."
                )
                username = os.environ.get(
                    "SPLUNK_USERNAME", "admin"
                )  # Fallback to environment variable
            if not username:
                _LOGGER.critical("[USERNAME ERROR] Username is required but missing.")
                raise RuntimeError("Username is required but missing.")

            if not splunkd_uri:
                _LOGGER.warning(
                    "[SPLUNKD URI WARNING] Splunkd URI not found in metadata. Attempting to retrieve from environment."
                )
                splunkd_uri = os.environ.get(
                    "SPLUNK_BASE_URL", "https://localhost:8089"
                )  # Fallback to environment variable
            if not splunkd_uri:
                _LOGGER.critical(
                    "[SPLUNKD URI ERROR] splunkd_uri is required but missing."
                )
                raise RuntimeError("Splunkd URI is required but missing.")

        except Exception as e:
            _LOGGER.exception(
                "[FEEDBACKEXPORT ERROR] An error occurred in the stream function: %s",
                str(e),
            )
            raise

        # If customer_name is not provided, retrieve it using _get_customer_name
        if not self.customer_name:
            try:
                _LOGGER.debug("[CUSTOMER NAME] Attempting to retrieve customer name.")
                self.customer_name = _get_customer_name(
                    base_url, session_key, local_verify=self.verify
                )
                if self.customer_name:
                    _LOGGER.debug(
                        "[CUSTOMER NAME SUCCESS] Retrieved customer name: %s",
                        self.customer_name,
                    )
                else:
                    _LOGGER.warning(
                        "[CUSTOMER NAME WARNING] Customer name could not be retrieved. Using default value."
                    )
                    self.customer_name = "default_customer_name"
            except Exception as e:
                _LOGGER.exception(
                    "[CUSTOMER NAME ERROR] Failed to retrieve customer name: %s", str(e)
                )
                self.customer_name = "default_customer_name"

        # If username is not provided, retrieve it using _get_user
        if not self.username:
            try:
                _LOGGER.debug(
                    "[USER FETCH] Attempting to retrieve and compare usernames."
                )
                user_message = _get_user(
                    base_url, session_key, current_username="", local_verify=self.verify
                )
                if user_message:
                    _LOGGER.debug("[USER NAME SUCCESS] %s", user_message)
                    self.username = user_message.split(":")[
                        -1
                    ].strip()  # Extract the username from the message
                else:
                    _LOGGER.warning(
                        "[USER FETCH WARNING] Username could not be retrieved. Using default value."
                    )
                    self.username = "default_username"
            except Exception as e:
                _LOGGER.exception(
                    "[USER FETCH ERROR] Failed to retrieve or compare usernames: %s",
                    str(e),
                )
                self.username = "default_username"

        # Continue with the existing logic for processing events...
        _LOGGER.debug("[STREAM] Processing incoming events.")
        for rec in records:
            self._events.append(rec)
            yield rec

        # Commenting out early return
        # if not self._events:
        #     _LOGGER.warning(
        #         "[STREAM] No events to process for customer '%s'. Skipping upload.",
        #         self.customer_name,
        #     )
        #     return

        _LOGGER.debug(
            "[STREAM] Successfully processed %d events for customer '%s'.",
            len(self._events),
            self.customer_name,
        )

        try:
            # Retrieve credentials for the specified username and realm
            username = self.username
            realm = "is4s_data_export"
            password = _read_password(
                username=username,
                realm="is4s_data_export",
                base_url=base_url,
                session_key=session_key,
                local_verify=self.verify,
            )

            # Validate that the retrieved password is non-empty and a string
            if not isinstance(password, str) or not password.strip():
                raise ValueError(
                    f"Invalid or empty password for '{username}' in realm '{realm}'."
                )

            _LOGGER.debug(
                "[CREDENTIALS] Successfully retrieved and validated password for user '%s' in realm '%s'.",
                username,
                realm,
            )
        except (ValueError, RuntimeError) as e:
            _LOGGER.error(
                "[CREDENTIALS] Failed to retrieve password for user '%s' in realm '%s'. Error: %s. Falling back to default password.",
                username,
                realm,
                str(e),
            )
            password = "changeme"
        except Exception as e:
            _LOGGER.exception(
                "[CREDENTIALS] Unexpected error occurred: %s. Using fallback password.",
                str(e),
            )
            password = "changeme"

        # Convert events to JSON and compress them into a ZIP file.
        _LOGGER.debug("[STREAM] Preparing to upload file.")
        passwd = password
        passwd_enc = _encrypt_password(passwd, self.target_url)

        try:

            _LOGGER.debug(
                "[ZIP CREATION] Preparing to compress %d events into a ZIP file for customer '%s'.",
                len(self._events),
                self.customer_name,
            )

            buff = io.BytesIO()
            try:
                with zipfile.ZipFile(buff, "w", zipfile.ZIP_DEFLATED) as zf:
                    # # First, process events that have KPI data (original data export format)
                    # for item in self._events:
                    #     try:
                    #         # Generate a sanitized filename based on the KPI name
                    #         kpi_name = item.get(
                    #             "kpi", "unknown_kpi"
                    #         )  # Default to "unknown_kpi" if missing
                    #         sanitized_kpi_name = kpi_name.replace(" ", "_")
                    #         filename = f"{sanitized_kpi_name}.json"
                    #         # Handle the "data" field if it exists
                    #         if "data" in item:
                    #             # If data is a list, join the entries into a single string separated by newlines
                    #             if isinstance(item["data"], list):
                    #                 item["data"] = "\n".join(
                    #                     entry for entry in item["data"]
                    #                 )
                    #             # If data is already a string, leave it as is
                    #             elif isinstance(item["data"], str):
                    #                 item["data"] = item["data"]

                    #             # Write the file content to the ZIP archive
                    #             zf.writestr(filename, item["data"])
                    #     except Exception as item_exc:
                    #         _LOGGER.error(
                    #             "[ITEM ERROR] Failed to process item: %s. Error: %s",
                    #             item,
                    #             str(item_exc),
                    #         )
                    #         continue  # Log the error and proceed with the next item
                    
                    # Run a separate search to get feedback data for feedback_export.json
                    _LOGGER.debug("[FEEDBACK SEARCH] Running feedback search to populate feedback_export.json.")
                    feedback_results = _run_feedback_search(
                        base_url=base_url,
                        session_key=session_key,
                        earliest_time="-24h",
                        latest_time="now",
                        local_verify=self.verify,
                    )
                    
                    # Create feedback_export.json from the feedback search results
                    feedback_content = ""
                    for item in feedback_results:
                        try:
                            # Convert each event to a JSON string and add a newline
                            feedback_content += json.dumps(item) + "\n"
                        except Exception as item_exc:
                            _LOGGER.error(
                                "[ITEM ERROR] Failed to serialize item for feedback_export.json: %s. Error: %s",
                                item,
                                str(item_exc),
                            )
                            continue
                    
                    # Write the combined feedback content to a single file in the ZIP
                    if feedback_content:
                        zf.writestr("feedback_export.json", feedback_content.rstrip())
                        _LOGGER.debug(
                            "[ZIP CREATION] Successfully created feedback_export.json with %d feedback events.",
                            len(feedback_results),
                        )
                    else:
                        _LOGGER.warning("[ZIP CREATION] No feedback events found to write to feedback_export.json.")
                    
                    _LOGGER.debug(
                        "[ZIP CREATION] ZIP file creation completed.",
                    )
                
                zip_bytes = buff.getvalue()
            except Exception as zip_exc:
                _LOGGER.critical(
                    "[ZIP ERROR] Failed to create ZIP file for customer '%s'. Error: %s",
                    self.customer_name,
                    str(zip_exc),
                )
                raise

            _LOGGER.debug("[STREAM] Preparing to upload file.")
            try:
                _LOGGER.debug(
                    "[UPLOAD] Starting upload for customer '%s'.", self.customer_name
                )
                customer_name = self.customer_name
                _upload_file(
                    zip_bytes,
                    filename=f"{customer_name.replace(' ', '_')}-is4s-feedback-export.zip",
                    base_url=self.target_url,
                    username=self.username,
                    password=passwd_enc,
                )
            except Exception as upload_exc:
                _LOGGER.critical(
                    "[UPLOAD ERROR] Failed to upload file for customer '%s'. Error: %s",
                    self.customer_name,
                    str(upload_exc),
                )
                raise
        except Exception as exc:
            _LOGGER.critical(
                "[CRITICAL ERROR] Failed to process and upload data for customer '%s'. Error: %s",
                self.customer_name,
                str(exc),
            )
            raise

    def finish(self):
        _LOGGER.debug("[FINISH] FeedbackExport execution completed.")


# Splunk entry‑point
if __name__ == "__main__":
    _LOGGER.debug("[MAIN] Starting FeedbackExport command dispatch.")
    dispatch(FeedbackExport, module_name=__name__)
