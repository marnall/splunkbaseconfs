# -----------------------------------------------
# ScheduledExport Custom Splunk Command
# -----------------------------------------------
# This script defines a Splunk custom generating command to:
# 1. Discover KPI searches from ssef and searchbase configuration.
# 2. Run each KPI search and collect results.
# 3. Compress results into an in-memory ZIP file.
# 4. Upload the ZIP file to a remote REST endpoint.
# -----------------------------------------------

from __future__ import absolute_import, print_function

import base64
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from typing import Dict, List, Optional, Union

import requests
from splunklib.searchcommands import (
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
    validators,
)
from splunklib.results import JSONResultsReader
import splunklib.results as splunklib_results

# -----------------------------------------------
# Global Configuration and Logger Initialization
# -----------------------------------------------

_SPLUNK_HOME = os.environ.get("SPLUNK_HOME", "/opt/splunk")
_LOG_PATH = os.path.join(_SPLUNK_HOME, "var", "log", "splunk", "scheduledexport.log")

_LOGGER = logging.getLogger("scheduledexport")
_LOGGER.setLevel(logging.WARNING)

if not _LOGGER.handlers:
    _fh = logging.FileHandler(_LOG_PATH)
    _formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
    _formatter.converter = time.gmtime
    _fh.setFormatter(_formatter)
    _LOGGER.addHandler(_fh)

    _sh = logging.StreamHandler(sys.stderr)
    _sh.setLevel(logging.WARNING)
    _sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    _LOGGER.addHandler(_sh)

    _LOGGER.propagate = False

_LOGGER.debug("[INIT] Logger initialized for the ScheduledExport script.")


# -----------------------------------------------
# Discovery SPL Template
# -----------------------------------------------
# Discovers KPI searches from ssef collections and searchbase configuration.
# The {collection_filter} placeholder is replaced at runtime with the
# configured collection name(s).

_DISCOVERY_SEARCH = (
    '| rest splunk_server=local /servicesNS/-/-/configs/conf-ssef '
    '| search title=* searches=* '
    '| makemv delim="," searches '
    '| rename searches as source , collection_name as collection_display_name, '
    'title as collection_name , description as collection_description , '
    'platform as collection_platform '
    '| fields collection_name collection_display_name collection_description '
    'collection_platform source '
    '| rex field=collection_name mode=sed "s/^ssef_collection:\\/\\///g" '
    '| stats latest(*) as * by collection_name source '
    '| search collection_name IN ({collection_filter}) '
    '| join source '
    '    [| rest /servicesNS/-/-/configs/conf-searchbase splunk_server=local '
    '    | rename eai:acl.app as app , eai:acl.removable as acl_removable '
    '    | eval tags=split(tags,",") '
    '    | search app=splunk_insights diagnostic_searches=* tags=KPIs '
    '    | stats count values(title) as title by diagnostic_searches '
    '    | rename title as child diagnostic_searches as source '
    '    | eval child=mvjoin(child,"|") ] '
    '| fields collection_name collection_display_name source child default_viz '
    '| eval child=split(child,"|") '
    '| stats count by child '
    '| join child '
    '    [| rest /servicesNS/-/-/configs/conf-searchbase splunk_server=local '
    '    | rename eai:acl.app as app , eai:acl.removable as acl_removable '
    '    | eval tags=split(tags,",") '
    '    | search app=splunk_insights '
    '    | rename title as child '
    '    | fields child search default_viz ] '
    '| search default_viz!=splunk.table '
    '| table child search '
    '| eval run_me = "| ssef adhoc=\\"" . child . "\\" time_from_searchbase=false '
    '| rename _time as timechart_time" '
    '| eval kpi = lower(child) '
    '| rex field=kpi mode=sed "s/\\s+/_/g" '
    '| table kpi run_me'
)


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
        url: Target URL for the GET request.
        headers: HTTP headers to include in the request.
        local_verify: How to call requests verify.

    Returns:
        Parsed JSON response.
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
        info = _http_get_json(key_url, headers=headers)
        if info.get("status_code") != 200:
            _LOGGER.error(
                "[ENCRYPTION ERROR] Unable to retrieve public key. Status: '%s'.",
                info.get("status_code"),
            )
            raise RuntimeError("Failed to retrieve public key for encryption.")

        pub_pem = info["data"]["publicKey"].encode()
        _LOGGER.debug("[ENCRYPTION] Successfully retrieved public key from server.")

        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(pub_pem)
            pub_path = tf.name

        res = subprocess.run(
            ["openssl", "rsautl", "-encrypt", "-pubin", "-inkey", pub_path],
            input=clear_pass.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

        os.remove(pub_path)

        return base64.b64encode(res.stdout).decode()
    except Exception as exc:
        _LOGGER.error(
            "[ENCRYPTION FAILED] Falling back to clear password over TLS. Error: %s",
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
    POST *file_bytes* to /upload/types using multipart/form-data.
    """
    _LOGGER.debug("[UPLOAD] Starting file upload process.")

    url = base_url.rstrip("/") + "/upload/types/insightsuite"

    auth_token = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_token}",
        "X-SPLUNK-UPLOAD": "splunk-app-scma",
    }

    files = {"upload": (filename, file_bytes, "application/zip")}

    try:
        _LOGGER.debug("[UPLOAD] Initiating file upload to endpoint")
        response = requests.post(url, files=files, headers=headers)
        response.raise_for_status()

        data = response.json()
        if data.get("status_code") != 200:
            _LOGGER.error(
                "[UPLOAD ERROR] Failed with status code %s and message: %s",
                data.get("status_code"),
                data.get("msg"),
            )
            return False

        file_destination = data.get("data", {}).get("fileDestination", "")
        download_url = f"https://downloadsvc.splunk.com/download/{file_destination}"
        _LOGGER.debug(
            "[UPLOAD SUCCESS] File uploaded. Download URL: '%s'", download_url
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
    Retrieves the password for the given username and realm from Splunk's
    storage/passwords endpoint. Returns an empty string on failure.
    """
    _LOGGER.debug(
        "[PASSWORD RETRIEVAL] Starting for username '%s'.", username
    )

    url = (
        f"{base_url}/servicesNS/nobody/splunk_insights/storage/passwords"
        f"/{realm}:{username}?output_mode=json"
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {session_key}",
    }

    try:
        response = requests.get(url, headers=headers, verify=local_verify)
        response.raise_for_status()

        data = response.json()
        if "entry" not in data or not data["entry"]:
            _LOGGER.warning(
                "[PASSWORD RETRIEVAL WARNING] Not found for '%s' in realm '%s'.",
                username,
                realm,
            )
            return ""

        password = data["entry"][0]["content"]["clear_password"]
        _LOGGER.debug(
            "[PASSWORD RETRIEVAL] Success for '%s' in realm '%s'.",
            username,
            realm,
        )
        return password

    except requests.exceptions.HTTPError as errh:
        if errh.response.status_code == 404:
            _LOGGER.warning(
                "[PASSWORD RETRIEVAL WARNING] Not found for '%s' in realm '%s'.",
                username,
                realm,
            )
            return ""
        else:
            _LOGGER.error(
                "[PASSWORD RETRIEVAL ERROR] HTTP error: %s", errh
            )
    except Exception as exc:
        _LOGGER.exception(
            "[EXCEPTION] Unexpected error during password retrieval: %s", exc
        )

    return ""


def _get_user(
    base_url: str,
    session_key: str,
    current_username: str,
    local_verify: Union[str, bool],
) -> Optional[str]:
    """
    Fetches the stored username from Splunk's storage/passwords endpoint
    and compares it with the current username.
    """
    url = (
        f"{base_url}/servicesNS/nobody/splunk_insights/storage/passwords"
        f"?output_mode=json"
    )

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
                entry = next(
                    (
                        e
                        for e in data["entry"]
                        if e["content"].get("realm") == "is4s_data_export"
                    ),
                    None,
                )

                if entry:
                    stored_username = str(
                        entry["content"]["username"]
                    ).replace('"', "")

                    if stored_username == current_username:
                        return None
                    else:
                        return (
                            f"The current configured user is: {stored_username}"
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
    """
    url = (
        f"{base_url}/servicesNS/-/splunk_insights/configs/conf-macros"
        f"/ssef_customer_name?output_mode=json"
    )

    headers = {"Authorization": f"Bearer {session_key}"}

    try:
        response = requests.get(url, headers=headers, verify=local_verify)

        if 200 <= response.status_code <= 299:
            data = response.json()
            customer_name = str(data["entry"][0]["content"]["definition"])
            return customer_name.replace('"', "")
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


# -----------------------------------------------
# Splunk Search Command definition
# -----------------------------------------------


_LOGGER.debug("[CONFIGURATION] Initializing Splunk command configuration.")

_SEARCH_POLL_INTERVAL = 5
_SEARCH_MAX_WAIT_DEFAULT = 600


@Configuration(type="reporting")
class ScheduledExport(GeneratingCommand):
    """
    Splunk Custom Generating Command: ScheduledExport

    This command performs the following steps:
    1. Runs a discovery search to identify KPI searches from ssef
       collections and searchbase configuration.
    2. Iterates over each discovered KPI and runs its search.
    3. Collects the results and compresses them into a ZIP archive
       (one JSON file per KPI).
    4. Uploads the ZIP file to a specified remote REST API endpoint.

    Configuration:
    - type="reporting" for generating command.
    - Optional options: username, customer_name, local_verify,
      collection_filter, max_kpi_wait.
    """

    target_url = "https://uploadsvc.splunk.com/api/v2"

    username = Option(require=False)
    customer_name = Option(require=False)
    local_verify = Option(require=False, default="true")
    collection_filter = Option(
        require=False, default="ssef_cloud_collection"
    )
    max_kpi_wait = Option(
        require=False, default=600, validate=validators.Integer()
    )
    debug = Option(require=False, default="false")

    def generate(self):
        """Main entry point for the generating command."""
        if (
            hasattr(self.debug, "lower")
            and self.debug.lower() == "true"
        ):
            _LOGGER.setLevel(logging.DEBUG)

        _LOGGER.debug("[GENERATE] Starting ScheduledExport command.")

        verify = self._parse_verify()
        session_key = self._extract_session_key()
        base_url = self._extract_base_url()

        customer_name = self._resolve_customer_name(
            base_url, session_key, verify
        )
        export_username = self._resolve_username(
            base_url, session_key, verify
        )

        # Step 1: Discover KPI searches
        _LOGGER.debug("[DISCOVERY] Running discovery search.")
        discovery_results = self._run_discovery_search()

        if not discovery_results:
            _LOGGER.warning("[DISCOVERY] No KPI searches found.")
            yield {
                "_time": time.time(),
                "kpi": "",
                "status": "no_kpis_found",
                "message": "Discovery search returned no KPI searches.",
                "result_count": 0,
            }
            return

        _LOGGER.debug(
            "[DISCOVERY] Found %d KPI searches.", len(discovery_results)
        )

        # Step 2: Run each KPI search and collect results
        kpi_data = {}
        kpi_statuses = []

        for kpi_info in discovery_results:
            kpi_name = kpi_info.get("kpi", "unknown_kpi")
            run_me = kpi_info.get("run_me", "")

            if not run_me:
                _LOGGER.warning(
                    "[KPI SEARCH] Skipping '%s': no run_me search defined.",
                    kpi_name,
                )
                kpi_statuses.append(
                    {
                        "_time": time.time(),
                        "kpi": kpi_name,
                        "status": "skipped",
                        "message": "No search defined.",
                        "result_count": 0,
                    }
                )
                continue

            _LOGGER.debug(
                "[KPI SEARCH] Running search for KPI '%s'.", kpi_name
            )

            try:
                results = self._run_kpi_search(run_me)
                kpi_data[kpi_name] = results

                kpi_statuses.append(
                    {
                        "_time": time.time(),
                        "kpi": kpi_name,
                        "status": "success",
                        "result_count": len(results),
                    }
                )
                _LOGGER.debug(
                    "[KPI SEARCH] KPI '%s' returned %d results.",
                    kpi_name,
                    len(results),
                )
            except Exception as exc:
                _LOGGER.error(
                    "[KPI SEARCH] Failed for '%s': %s", kpi_name, str(exc)
                )
                kpi_statuses.append(
                    {
                        "_time": time.time(),
                        "kpi": kpi_name,
                        "status": "failed",
                        "message": str(exc),
                        "result_count": 0,
                    }
                )

        if not kpi_data:
            _LOGGER.warning(
                "[EXPORT] No KPI data collected. Skipping upload."
            )
            for status in kpi_statuses:
                yield status
            return

        # Step 3: Get credentials and encrypt password
        password = self._get_export_password(
            export_username, base_url, session_key, verify
        )
        passwd_enc = _encrypt_password(password, self.target_url)

        # Step 4: Create ZIP
        try:
            zip_bytes = self._create_zip(kpi_data)
        except Exception as exc:
            _LOGGER.critical(
                "[ZIP ERROR] Failed to create ZIP: %s", str(exc)
            )
            yield {
                "_time": time.time(),
                "kpi": "",
                "status": "zip_creation_failed",
                "message": str(exc),
                "result_count": 0,
            }
            return

        # Step 5: Upload
        upload_status = "upload_failed"
        try:
            safe_customer = customer_name.replace(" ", "_")
            filename = f"{safe_customer}-is4s-scheduled-export.zip"
            upload_success = _upload_file(
                zip_bytes,
                filename=filename,
                base_url=self.target_url,
                username=export_username,
                password=passwd_enc,
            )

            if upload_success:
                upload_status = "upload_success"
            _LOGGER.debug("[UPLOAD] Upload status: %s", upload_status)
        except Exception as exc:
            _LOGGER.critical("[UPLOAD ERROR] %s", str(exc))

        # Step 6: Yield status events for each KPI
        for status in kpi_statuses:
            status["upload_status"] = upload_status
            status["customer_name"] = customer_name
            yield status

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    def _parse_verify(self) -> bool:
        if (
            hasattr(self.local_verify, "lower")
            and self.local_verify.lower() == "true"
        ):
            return True
        return False

    def _extract_session_key(self) -> str:
        session_key = None
        if hasattr(self._metadata, "searchinfo"):
            searchinfo = self._metadata.searchinfo
            if hasattr(searchinfo, "session_key"):
                session_key = searchinfo.session_key
            elif isinstance(searchinfo, dict):
                session_key = searchinfo.get("session_key")

        if not session_key:
            session_key = os.environ.get("SPLUNK_SESSION_KEY")
        if not session_key:
            raise RuntimeError("Session key is required but missing.")
        return session_key

    def _extract_base_url(self) -> str:
        base_url = None
        if hasattr(self._metadata, "searchinfo"):
            searchinfo = self._metadata.searchinfo
            if hasattr(searchinfo, "splunkd_uri"):
                base_url = searchinfo.splunkd_uri
            elif isinstance(searchinfo, dict):
                base_url = searchinfo.get("splunkd_uri")

        if not base_url:
            base_url = os.environ.get(
                "SPLUNK_BASE_URL", "https://localhost:8089"
            )
        return base_url

    def _resolve_customer_name(
        self, base_url: str, session_key: str, verify: bool
    ) -> str:
        if self.customer_name:
            return self.customer_name

        try:
            name = _get_customer_name(
                base_url, session_key, local_verify=verify
            )
            if name:
                return name
        except Exception as e:
            _LOGGER.exception("[CUSTOMER NAME ERROR] %s", str(e))

        return "default_customer_name"

    def _resolve_username(
        self, base_url: str, session_key: str, verify: bool
    ) -> str:
        if self.username:
            return self.username

        try:
            user_message = _get_user(
                base_url,
                session_key,
                current_username="",
                local_verify=verify,
            )
            if user_message:
                return user_message.split(":")[-1].strip()
        except Exception as e:
            _LOGGER.exception("[USER FETCH ERROR] %s", str(e))

        return "default_username"

    def _get_export_password(
        self,
        username: str,
        base_url: str,
        session_key: str,
        verify: bool,
    ) -> str:
        try:
            password = _read_password(
                username=username,
                realm="is4s_data_export",
                base_url=base_url,
                session_key=session_key,
                local_verify=verify,
            )
            if not isinstance(password, str) or not password.strip():
                raise ValueError(
                    f"Invalid or empty password for '{username}'."
                )
            return password
        except Exception as e:
            _LOGGER.error(
                "[CREDENTIALS] Failed for '%s': %s. Using fallback.",
                username,
                str(e),
            )
            return "changeme"

    def _run_discovery_search(self) -> List[Dict]:
        """Run the discovery SPL to find KPI searches."""
        search_spl = _DISCOVERY_SEARCH.format(
            collection_filter=self.collection_filter
        )
        _LOGGER.debug(
            "[DISCOVERY] Dispatching SPL (collection_filter=%s):\n%s",
            self.collection_filter,
            search_spl,
        )
        return self._dispatch_and_collect(search_spl)

    def _run_kpi_search(self, run_me: str) -> List[Dict]:
        """Run a single KPI search and return its results."""
        max_wait = (
            int(self.max_kpi_wait)
            if self.max_kpi_wait
            else _SEARCH_MAX_WAIT_DEFAULT
        )
        return self._dispatch_and_collect(run_me, max_wait=max_wait)

    def _dispatch_and_collect(
        self,
        search_spl: str,
        max_wait: int = _SEARCH_MAX_WAIT_DEFAULT,
    ) -> List[Dict]:
        """
        Dispatch a search job via the Splunk SDK, wait for completion,
        and return all results as a list of dicts.
        """
        search_stripped = search_spl.strip()
        if not search_stripped.startswith("|") and not search_stripped.lower().startswith("search "):
            search_spl = f"search {search_stripped}"

        job = self.service.jobs.create(
            search_spl,
            exec_mode="normal",
            output_mode="json",
        )
        _LOGGER.debug("[SEARCH JOB] Created job SID: %s", job.sid)

        elapsed = 0
        while not job.is_done():
            time.sleep(_SEARCH_POLL_INTERVAL)
            elapsed += _SEARCH_POLL_INTERVAL
            if elapsed >= max_wait:
                _LOGGER.error(
                    "[SEARCH JOB] Timed out after %d seconds. SID: %s",
                    max_wait,
                    job.sid,
                )
                try:
                    job.cancel()
                except Exception:
                    pass
                return []

        dispatch_state = (
            job.state.content.get("dispatchState", "").upper()
        )
        if dispatch_state == "FAILED":
            _LOGGER.error("[SEARCH JOB] Failed. SID: %s", job.sid)
            return []

        results = []
        offset = 0
        page_size = 10000
        result_count = int(job["resultCount"])

        while offset < result_count:
            job_results = job.results(
                output_mode="json", count=page_size, offset=offset
            )
            for result in JSONResultsReader(job_results):
                if isinstance(result, splunklib_results.Message):
                    continue
                results.append(result)
            offset += page_size

        _LOGGER.debug(
            "[SEARCH JOB] Collected %d results from SID: %s",
            len(results),
            job.sid,
        )
        return results

    def _create_zip(self, kpi_data: Dict[str, List[Dict]]) -> bytes:
        """
        Compress KPI results into a ZIP archive.
        Each KPI produces one JSON file (<kpi_name>.json) containing
        a pretty-printed JSON array, matching the React export format.
        """
        buff = io.BytesIO()
        with zipfile.ZipFile(buff, "w", zipfile.ZIP_DEFLATED) as zf:
            for kpi_name, results in kpi_data.items():
                filename = f"{kpi_name}.json"

                try:
                    file_content = json.dumps(results, indent=2)
                except Exception as exc:
                    _LOGGER.error(
                        "[ZIP] Failed to serialize results for '%s': %s",
                        kpi_name,
                        str(exc),
                    )
                    continue

                zf.writestr(filename, file_content)
                _LOGGER.debug(
                    "[ZIP] Added '%s' with %d results.",
                    filename,
                    len(results),
                )

        return buff.getvalue()


# Splunk entry-point
if __name__ == "__main__":
    _LOGGER.debug("[MAIN] Starting ScheduledExport command dispatch.")
    dispatch(ScheduledExport, module_name=__name__)
