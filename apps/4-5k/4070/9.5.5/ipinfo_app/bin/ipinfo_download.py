import datetime
import os
import traceback

import requests
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
import splunk.clilib.cli_common as scc

from ipinfo.logging import get_logger
from ipinfo.utils import build_proxy, get_config as get_conf
from ipinfo_constants import FILE_NAME_URLS_MAPPING, LIST_OF_FILES_TO_EXCLUDE
from ipinfo_utils import get_config, get_management_uri, get_service, get_service_from_session_key, post_message


logger = get_logger(__file__)


def get_credentials_from_splunk(session_key, bearer_token):
    logger.debug("Retrieving credentials from Splunk")
    splunkd_uri = scc.getMgmtUri()
    logger.debug("Splunkd URI: %s", splunkd_uri)

    service = None
    if bearer_token != "":
        logger.debug("Creating service with bearer token")
        service = get_service(splunkd_uri, bearer_token)
    else:
        logger.debug("Creating service with session key")
        service = get_service_from_session_key(splunkd_uri, session_key)

    if service is None:
        logger.error("Cannot access Splunk service")
        raise ValueError("Cannot access Splunk service")

    storage_passwords = service.storage_passwords
    if storage_passwords is None:
        logger.error("Could not resolve storage passwords for IPinfo application")
        raise ValueError("Could not resolve storage passwords for IPinfo application")

    logger.debug("Retrieving credentials from storage passwords")
    token = ""
    proxy_password = ""
    for storage_password in storage_passwords.list():
        if storage_password.realm == "ipinfo":
            if storage_password.username == "token":
                token = storage_password.clear_password
                logger.debug("Token retrieved from storage")
            elif storage_password.username == "proxy_password":
                proxy_password = storage_password.clear_password
                logger.debug("Proxy password retrieved from storage")

    logger.debug("Credentials retrieved successfully")
    return token, proxy_password


def download_mmdb_file(session_key, bearer_token, mmdb_file):
    logger.debug("Starting download for MMDB file: %s", mmdb_file)
    name = mmdb_file + ".mmdb"
    rename = mmdb_file + datetime.datetime.now().strftime("%m-%d-%Y_%H_%M_%S") + ".mmdb"
    path = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ipinfo_app", "lookups"])
    logger.debug("Download path: %s", path)

    logger.debug("Cleaning up existing files for: %s", mmdb_file)
    for dirpath, _, files in os.walk(path):
        for file in files:
            if file in LIST_OF_FILES_TO_EXCLUDE:
                logger.debug("Skipping excluded file: %s", file)
                continue
            elif file.startswith(mmdb_file):
                file_path = os.path.join(dirpath, file)
                logger.info("Removing existing file: %s", file_path)
                os.remove(file_path)

    service = get_service_from_session_key(get_management_uri(), session_key)

    logger.debug("Retrieving credentials for MMDB download")
    token = ""
    try:
        token, _ = get_credentials_from_splunk(session_key, bearer_token)
    except ValueError:
        pass

    if token == "":
        logger.error("Token not found or empty for MMDB download: %s", mmdb_file)
        logger.error("You might not have access to retrieve token or token is not set yet.")
        post_message(
            session_key,
            mmdb_file,
            "IPinfo error while downloading " + mmdb_file + ".mmdb. Check Log dashboard",
            "error",
        )
        return 1

    logger.debug("Token retrieved successfully")
    proxy_enable = get_config("proxy_enable")
    proxy = {}
    if proxy_enable == "Yes":
        proxy = build_proxy(service)
    else:
        logger.debug("Proxy is disabled")

    if not os.path.exists(path):
        logger.debug("Creating lookup path: %s", path)
        os.makedirs(path)

    old_file = os.path.join(path, name)
    new_file = os.path.join(path, rename)
    logger.info("Starting download for MMDB file: %s", mmdb_file)
    url = FILE_NAME_URLS_MAPPING[mmdb_file]
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "IPinfoClient/Splunk/9.5.5",
    }
    ca_cert_path = get_conf("ca_cert_path", service)
    # First attempt explicitly requests R2; on network-level failures we fall
    # back to an explicit GCS request. Both redirects come from the same
    # ipinfo.io endpoint so the firewall profile customers need to allow is
    # either dl.assets.ipinfo.io or storage.googleapis.com, whichever their
    # network permits.
    params = [{"r2": "true"}, {"r2": "false"}]
    response = None
    for index, param in enumerate(params):
        try:
            logger.debug("Downloading  %s with param %s", mmdb_file, param)
            response = requests.get(url, params=param, headers=headers, proxies=proxy, stream=True, verify=ca_cert_path or True)
            response.raise_for_status()
            logger.debug("Response status code: %d, content length: %s", response.status_code, response.headers.get("content-length", "unknown"))
            # If we reach this point the request was successful and we can keep going
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.SSLError, requests.exceptions.Timeout) as err:
            logger.warning("Network error downloading %s with param %s: %s", mmdb_file, param, err)
            if index == (len(params) - 1):
                logger.error("All download attempts failed for %s, last error: %s", mmdb_file, err)
                return 1
        except requests.exceptions.HTTPError as err:
            logger.error("HTTP error downloading %s with param %s: %s", mmdb_file, param, err)
            return 1

    # Silence type checkers
    assert response

    logger.debug("Writing downloaded content to file: %s", new_file)
    try:
        with open(new_file, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
    except requests.exceptions.ChunkedEncodingError as err:
        logger.error("Stream truncated while downloading %s: %s", mmdb_file, err)
        return 1

    logger.debug("Download completed, finalizing file")
    try:
        if os.path.exists(old_file):
            logger.debug("Removing old file: %s", old_file)
            os.remove(old_file)
        os.rename(new_file, old_file)
        logger.info("File downloaded successfully: %s", mmdb_file)
    except Exception as exc:
        logger.error("Error finalizing download of %s: %s", mmdb_file, exc)
        logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))
        return 1
    post_message(session_key, mmdb_file, "IPinfo " + mmdb_file + ".mmdb downloaded successfully", "info")
    return 0
