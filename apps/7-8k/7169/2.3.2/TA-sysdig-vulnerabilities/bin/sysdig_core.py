import copy
import os
import sqlite3
import time
import traceback
from urllib.parse import urlencode, urlparse, quote
from datetime import datetime, timedelta
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


def configure_retries(helper):
    """
    Configures the helper's HTTP session to retry on 429 and 5xx errors
    with intelligent backoff using x-ratelimit-reset headers.
    """
    if helper.rest_helper.http_session is None:
        # Initialize the session if it hasn't been created yet.
        helper.rest_helper._init_request_session(proxy_uri=helper._get_proxy_uri())

    class SysdigRetry(Retry):
        """
        Custom Retry class to handle Sysdig's specific rate limit headers.
        Falls back to standard Retry-After or exponential backoff.
        """
        def get_retry_after(self, response):
            # 1. Try standard Retry-After header first
            retry_after = super(SysdigRetry, self).get_retry_after(response)
            if retry_after is not None:
                return retry_after

            # 2. Try x-ratelimit-reset (Epoch timestamp)
            # The argument passed is the HTTPResponse object, so we access .headers
            reset_timestamp = response.headers.get("x-ratelimit-reset")
            if reset_timestamp:
                try:
                    # Calculate wait time: reset_time - now
                    sleep_time = float(reset_timestamp) - time.time()
                    # Add a small buffer (e.g. 1s) to be safe
                    return max(sleep_time, 0) + 1.0
                except (ValueError, TypeError):
                    pass
            
            return None

    # Create a custom SysdigRetry object.
    # We enable respect_retry_after_header=True so our custom get_retry_after is called.
    # Retry on rate limits (429) and temporary gateway/service issues (502-504).
    # HTTP 500 is excluded as it indicates a permanent server error that won't resolve with retries.
    retry_strategy = SysdigRetry(
        total=10,
        backoff_factor=2,  # Used if no headers are present
        status_forcelist=[429, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
        respect_retry_after_header=True,
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)

    # Mount the adapter for both http and https.
    helper.rest_helper.http_session.mount("https://", adapter)
    helper.rest_helper.http_session.mount("http://", adapter)
    helper.log_info("Configured custom SysdigRetry strategy: retries 429/502-504, skips 500")


def fetch_vulnerabilities(sdc_url, token, nvd_api_key, selected_fields, max_images, new_event, helper):
    use_proxy = helper.get_proxy() != {}

    if 'vuln_description' in selected_fields:
        init_db(helper)
        update_db(helper, use_proxy, nvd_api_key)

    next_page = 'firstPage'
    results = []

    # Get ALL runtime results
    while (next_page):
        ok, results_page = request_runtime_results(helper, sdc_url, token, use_proxy, next_page)
        if not ok:
            helper.log_error("Unable to retrieve runtime results: {}".format(results_page))
            return

        results += results_page['data']
        if 'next' in results_page['page']:
            next_page = results_page['page']['next']
        else:
            next_page = None

    # Prune non-unique images from runtime results by comparing data mainAssetName
    # since they could be used for running multiple containers
    # Remove results that do not have any vulnerability
    known_images = dict()
    for asset in results:
        if (asset['vulnTotalBySeverity']['critical'] != 0 or asset['vulnTotalBySeverity']['high'] != 0 or asset['vulnTotalBySeverity']['medium'] != 0 or asset['vulnTotalBySeverity']['low'] != 0 or asset['vulnTotalBySeverity']['negligible'] != 0):
            if (asset['mainAssetName'] not in known_images):
                # assetMetadata needs to be created since it is going to hold all workloads, or hosts,
                # that are created out of this asset
                asset.update({'assetMetadata': [asset['scope']]})
                copy_of_asset = copy.deepcopy(asset)
                known_images[asset['mainAssetName']] = copy_of_asset
                del copy_of_asset['scope']
                helper.log_debug("Added this asset {}".format(asset['resultId']))
            else:
                # assetMetadata gets updated here when asset is already in known_images, but workload/host is different
                known_images[asset['mainAssetName']]['assetMetadata'].append(asset['scope'])

    helper.log_info("Found {} images in the results, out of which {} are unique and have vulnerabilities".format(
        len(results),
        len(known_images)))

    # Sort by image name
    sorted_images = sorted(known_images.values(), key=lambda v: v["mainAssetName"], reverse=True)

    try:
        if max_images and int(max_images):
            sorted_images = sorted_images[:int(max_images)]
            helper.log_warning("Limiting max number of images to: {}".format(max_images))
    except:
        helper.log_warning("Error parsing max number of images: {}".format(max_images))

    for idx, asset in enumerate(sorted_images):
        try:

            fulltag = asset["mainAssetName"]

            ok, result = request_single_runtime_result_by_id(helper, sdc_url, token, use_proxy, asset['resultId'])
            if not ok:
                helper.log_error("Unable to load results for id={} fulltag={} (skipping): {}".format(
                    asset['resultId'],
                    fulltag,
                    result))
                continue

            # Is it a container or machine, VM,...
            # v1 API: no 'result' wrapper, and 'type' renamed to 'assetType'
            hostType = result['assetType']
            metadata = result['metadata']

            current_asset = {
                'fulltag': fulltag,
                'type': hostType,
                'assetMetadata': asset['assetMetadata'],
                'url': getBackLink(sdc_url, asset)
            }

            if 'hostId' in metadata:
                current_asset['hostId'] = metadata['hostId']
                current_asset['assetId'] = metadata['hostId']
            if 'hostName' in metadata:
                current_asset['hostName'] = metadata['hostName']
            if 'imageId' in metadata:
                current_asset['imageId'] = metadata['imageId']
                current_asset['assetId'] = metadata['imageId']
            if 'digest' in metadata:
                current_asset['imageDigest'] = metadata['digest']
            if 'createdAt' in metadata:
                current_asset['createdAt'] = metadata['createdAt']
            if 'architecture' in metadata:
                current_asset['architecture'] = metadata['architecture']
            if 'os' in metadata:
                current_asset['os'] = metadata['os']
            if 'baseOs' in metadata:
                current_asset['baseOs'] = metadata['baseOs']
            if 'labels' in metadata:
                current_asset['labels'] = metadata['labels']
            if 'layersCount' in metadata:
                current_asset['layersCount'] = metadata['layersCount']
            if 'pullString' in metadata:
                current_asset['pullString'] = metadata['pullString']
            if 'size' in metadata:
                current_asset['size'] = metadata['size']
            if 'author' in metadata:
                current_asset['author'] = metadata['author']

            helper.log_info("({}/{}) Processing fulltag={}".format(
                idx + 1, len(sorted_images),
                fulltag))

            packages_map = result.get('packages', {})
            vulnerabilities_map = result.get('vulnerabilities', {})

            for package_id, package in packages_map.items():

                # Get vulnerability references from package
                # Use 'or []' to handle None values from API
                vuln_refs = package.get('vulnerabilitiesRefs') or []

                for vuln_ref in vuln_refs:
                    # Look up vulnerability in top-level map
                    vuln = vulnerabilities_map.get(vuln_ref)
                    if not vuln:
                        helper.log_warning("Vulnerability {} not found in vulnerabilities map for package {}".format(
                            vuln_ref, package.get('name', 'unknown')))
                        continue

                    vulnerability = {
                        # required
                        "package_type": package['type'],
                        "package_name": package['name'],
                        "package_version": package['version'],
                        "vuln": vuln['name'],
                        # v1 API: severity is now a direct string, not nested in 'value'
                        "severity": vuln['severity']
                    }

                    # optional
                    if 'package_data' in selected_fields:
                        if 'path' in package:
                            vulnerability["package_path"] = package['path']
                        if 'suggestedFix' in package:
                            vulnerability["package_suggestedFix"] = package['suggestedFix']
                            vulnerability["fix_available"] = True
                        else:
                            vulnerability["fix_available"] = False

                        # v1 API: 'inUse' renamed to 'isRunning'
                        if 'isRunning' in package:
                            vulnerability["package_inUse"] = package['isRunning']

                    vuln_details = vuln.copy()

                    # v1 API: 'fixVersion' renamed from 'fixedInVersion', but we need to keep
                    # the old field name for Splunk event compatibility
                    if 'fixVersion' in vuln_details:
                        vuln_details['fixedInVersion'] = vuln_details.pop('fixVersion')

                    # Remove redundant fields
                    if 'severity' in vuln_details:
                        del vuln_details['severity']

                    if 'vuln_description' in selected_fields:
                        vuln_details['description'] = lookup_cve_description(helper, vuln_details['name'])

                    data = {
                        'vulnerability_id': vuln_details['name'],
                        'asset': current_asset,
                        'vulnerability': vulnerability,
                        'vulnerability_details': vuln_details
                    }

                    new_event(fulltag, data)

        except Exception as e:
            helper.log_error("Unable to process fulltag {}:\n{}".format(fulltag, traceback.format_exc()))


def filter_runtime_images(known_images, runtime_images):
    known_runtime_images = dict()
    for image in runtime_images['images']:
        known_runtime_images[image['imageId']] = image

    image_tags = list(known_images.keys())
    for tag in image_tags:
        if known_images[tag]['imageId'] not in known_runtime_images:
            del known_images[tag]


def request_runtime_results(helper, sdc_url, token, use_proxy, next_page_cursor):
    cursor = '' if next_page_cursor == 'firstPage' else "?cursor=" + next_page_cursor
    url = "{base_url}/secure/vulnerability/v1/runtime-results{cursor}".format(
        base_url=sdc_url,
        cursor=cursor)
    authHeader = {'Authorization': 'Bearer ' + token}

    res = helper.send_http_request(url, "GET", headers=authHeader, verify=True, timeout=(10.0, 60.0), use_proxy=use_proxy)

    if not _checkResponse(helper, res):
        return [False, {}]

    return [True, res.json()]


def request_single_runtime_result_by_id(helper, sdc_url, token, use_proxy, resultId):
    url = "{base_url}/secure/vulnerability/v1/results/{resultId}".format(
        base_url=sdc_url,
        resultId=resultId)
    authHeader = {'Authorization': 'Bearer ' + token}

    res = helper.send_http_request(url, "GET", headers=authHeader, verify=True, timeout=(10.0, 60.0), use_proxy=use_proxy)

    if not _checkResponse(helper, res):
        return [False, {}]

    return [True, res.json()]


def _checkResponse(helper, res):
    # Check for client and server errors (4xx, 5xx).
    # 3xx redirects are handled automatically by the requests library.
    if res.status_code >= 400:
        helper.log_error(f"Sysdig API HTTP code {res.status_code}")

        try:
            j = res.json()
        except Exception:
            helper.log_error(f"Sysdig API error: {res.text}")
            return False
        if 'errors' in j:
            error_msgs = []
            for error in j['errors']:
                error_msg = []
                if 'message' in error:
                    error_msg.append(error['message'])

                if 'reason' in error:
                    error_msg.append(error['reason'])

                error_msgs.append(': '.join(error_msg))

            joined_errors = '\n'.join(error_msgs)
            helper.log_error(f"Sysdig API error {joined_errors}")
        elif 'message' in j:
            helper.log_error(f"Sysdig API error {j['message']}")
        return False
    return True


def getBackLink(sdc_url, asset):
    # Remove any trailing slash from the provided base URL
    base_url = sdc_url.rstrip("/")

    # Parse the URL to get the hostname (netloc)
    parsed_url = urlparse(base_url)
    domain = parsed_url.netloc

    # Build the path based on the domain
    if domain == "secure.sysdig.com":
        # For the default region, do not add '/secure/' in the path.
        path = "/#/vulnerabilities/runtime/"
    else:
        # For other regions, prepend with '/secure/'
        path = "/secure/#/vulnerabilities/runtime/"

    # Start building the filter query with the mainAssetName
    filters = []
    main_asset_name = asset.get("mainAssetName")
    if main_asset_name:
        filters.append(f'freeText in ("%s")' % main_asset_name)

    # Fields to optionally include in the filter
    filter_fields = [
        "kubernetes.cluster.name",
        "kubernetes.namespace.name",
        "kubernetes.workload.type",
        "kubernetes.workload.name",
        "kubernetes.pod.container.name",
    ]

    metadata = asset.get("assetMetadata", [])
    for field in filter_fields:
        # Collect unique values for the field from all metadata entries
        values = list({entry.get(field) for entry in metadata if field in entry})
        if values:
            quoted_values = ['"%s"' % v for v in values]
            if len(values) == 1:
                # Use "=" when there's a single value
                filters.append(f'{field} = {quoted_values[0]}')
            else:
                # Use "in (...)" when multiple values are present
                filters.append(f'{field} in (%s)' % ', '.join(quoted_values))
                print(f"Multiple values for {field}: {quoted_values}")

    # Encode the combined filter string for use in the URL
    raw_filter = " and ".join(filters)
    encoded_filter = quote(raw_filter, safe='')

    # Build the full backlink URL
    backlink = f"{base_url}{path}?filter={encoded_filter}"
    return backlink


# Global variable for the SQLite connection.
_db_connection = None


def init_db_connection(helper):
    """
    Initializes and returns a persistent SQLite connection.
    Must be called once at startup.
    """
    global _db_connection
    if _db_connection is None:
        db_path = get_db_path(helper)  # Reuse your get_db_path() function.
        # Use check_same_thread=False if you plan to use the connection from multiple threads.
        _db_connection = sqlite3.connect(db_path, check_same_thread=False)
        helper.log_debug(f"Persistent DB connection initialized at {db_path}")
    return _db_connection


def get_db_path(helper):
    app_name = helper.get_app_name()
    splunk_home = os.environ.get("SPLUNK_HOME", ".")
    db_dir = os.path.join(splunk_home, "var", "lib", app_name)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    return os.path.join(db_dir, "cve_cache.sqlite")


def init_db(helper):
    conn = init_db_connection(helper)
    cursor = conn.cursor()
    # Create the main CVE table.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cves (
            cve_id TEXT PRIMARY KEY,
            description TEXT,
            last_modified TEXT
        )
    ''')
    # Create a metadata table to store the last successful update timestamp.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()


def get_metadata(conn, key):
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM metadata WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None


def set_metadata(conn, key, value):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO metadata (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    ''', (key, value))
    conn.commit()


def process_vulnerabilities_page(vulnerabilities, cursor, helper):
    """
    Processes a list of vulnerabilities from NVD and updates the DB cursor.
    """
    for vuln in vulnerabilities:
        cve_obj = vuln.get("cve", {})
        cve_id = cve_obj.get("id")
        descriptions = cve_obj.get("descriptions", [])
        description = next((d.get("value") for d in descriptions if d.get("lang") == "en"), "No description provided")
        last_modified = cve_obj.get("lastModified")
        if cve_id:
            cursor.execute('''
                INSERT INTO cves (cve_id, description, last_modified)
                VALUES (?, ?, ?)
                ON CONFLICT(cve_id) DO UPDATE SET
                    description=excluded.description,
                    last_modified=excluded.last_modified
            ''', (cve_id, description, last_modified))
            helper.log_debug(f"Processed {cve_id} - {description}")


def get_nvd_data(url, helper, use_proxy, nvd_api_key=None):
    """
    Makes a GET request to the NVD API.
    Relies on the helper's configured session for retries (exponential backoff).
    Returns the JSON response if successful, or None otherwise.
    """
    # Build base headers
    headers = {"Accept": "application/json"}
    if nvd_api_key:
        headers["apiKey"] = nvd_api_key

    try:
        res = helper.send_http_request(
            url,
            method="GET",
            headers=headers,
            verify=True,
            timeout=(10.0, 60.0),
            use_proxy=use_proxy
        )
        if res.status_code == 200:
            return res.json()
        else:
            helper.log_error(f"NVD API HTTP error {res.status_code} for URL: {url}")
            return None
    except Exception as e:
        helper.log_error(f"Exception when calling NVD API: {traceback.format_exc()}")
        return None


def update_db(helper, use_proxy, nvd_api_key=None):
    """
    Updates the local CVE database from NVD.
    - If the DB is empty or the last update (stored in metadata) is older than 120 days,
      perform a full load (and clear the existing CVE data).
    - Otherwise, use the stored last update timestamp for an incremental update.
    - Pages through the results (2000 items per page), handling rate limits using exponential backoff.
    - Only if the entire update succeeds is the metadata table updated with the new timestamp,
      which is taken from the 'timestamp' field of the NVD API response.
    """
    base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    results_per_page = 2000

    conn = init_db_connection(helper)
    cursor = conn.cursor()

    # Retrieve the last successful update from metadata.
    last_update_str = get_metadata(conn, "last_nvd_update")
    full_load = False
    if last_update_str:
        try:
            last_update = datetime.fromisoformat(last_update_str)
            if datetime.utcnow() - last_update > timedelta(days=120):
                helper.log_info("Last update is older than 120 days. Performing a full load.")
                full_load = True
            else:
                helper.log_info(f"Incremental update from {last_update_str}")
        except Exception as e:
            helper.log_error(f"Error parsing last update date '{last_update_str}':\n{traceback.format_exc()}")
            full_load = True
    else:
        helper.log_info("No last update found. Performing full load.")
        full_load = True

    if full_load:
        helper.log_debug("Clearing existing CVE data for full load.")
        cursor.execute("DELETE FROM cves")
        conn.commit()

    # Build query parameters.
    params = {
        "resultsPerPage": results_per_page,
        "startIndex": 0
    }
    if not full_load:
        # Ensure stored timestamp is properly formatted (with a trailing Z).
        mod_start = datetime.fromisoformat(last_update_str).isoformat(timespec='seconds') + "Z"
        mod_end = datetime.utcnow().isoformat(timespec='seconds') + "Z"
        params["lastModStartDate"] = mod_start
        params["lastModEndDate"] = mod_end

    # Note: No API key in query params anymore.
    total_results = None
    success = True  # flag to indicate whether update succeeded
    last_response_timestamp = None  # will store the 'timestamp' field from NVD API

    # Process pages in a loop.
    while True:
        params["startIndex"] = params.get("startIndex", 0)
        query_string = urlencode(params)
        url = f"{base_url}?{query_string}"
        helper.log_info(f"Fetching URL: {url}")

        data = get_nvd_data(url, helper, use_proxy, nvd_api_key=nvd_api_key)
        if data is None:
            helper.log_error("Update aborted due to API errors.")
            success = False
            break

        # Capture the timestamp from the response.
        last_response_timestamp = data.get("timestamp", None)

        if total_results is None:
            total_results = data.get("totalResults", 0)
            helper.log_debug(f"Total vulnerabilities to process: {total_results}")

        vulnerabilities = data.get("vulnerabilities", [])
        if not vulnerabilities:
            helper.log_debug("No vulnerabilities returned; finishing update.")
            break

        process_vulnerabilities_page(vulnerabilities, cursor, helper)
        conn.commit()

        params["startIndex"] += results_per_page
        if params["startIndex"] >= total_results:
            helper.log_info("All vulnerabilities processed.")
            break

    # If the update was successful, update the metadata with the new update timestamp.
    if success:
        new_update = last_response_timestamp if last_response_timestamp else datetime.utcnow().isoformat(timespec='seconds')
        helper.log_info(f"Update succeeded. Setting last_nvd_update to {new_update}")
        set_metadata(conn, "last_nvd_update", new_update)
    else:
        helper.log_error("Update did not complete successfully. Metadata not updated.")

    helper.log_info("Database update completed.")


def lookup_cve_description(helper, cve_id):
    """
    Returns the CVE description from the local DB for the given CVE ID,
    or None if not found.
    """
    global _db_connection
    if _db_connection is None:
        init_db_connection(helper)
    cursor = _db_connection.cursor()
    cursor.execute("SELECT description FROM cves WHERE cve_id = ?", (cve_id,))
    row = cursor.fetchone()
    return row[0] if row else None
