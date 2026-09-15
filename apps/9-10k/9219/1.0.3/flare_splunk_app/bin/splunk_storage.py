import flare_constants as const
import logging
import requests as http_requests

from flare_ssl import UnverifiedHTTPAdapter


logger = logging.getLogger("flare_cron_job")


def _local_splunk_session() -> http_requests.Session:
    """Build a session for local splunkd REST calls with a pinned TLS context.

    Verification is disabled because splunkd presents a self-signed certificate
    on the loopback management port.
    """
    session = http_requests.Session()
    session.mount("https://", UnverifiedHTTPAdapter())
    return session


def get_session_token_from_stdin() -> str:
    """Reads and parses the Splunk session key provided securely via standard input."""
    import sys

    session_key = ""
    for line in sys.stdin:
        session_key = line

    raw_token_line = session_key.strip()
    if raw_token_line.startswith("sessionKey="):
        return raw_token_line.split("=", 1)[1]
    return raw_token_line


def get_storage_passwords(token: str) -> list:
    """Fetch storage/passwords from the local Splunk REST API."""
    headers = {"Authorization": f"Splunk {token}"}
    # count=0 disables pagination
    url = (
        f"https://{const.HOST}:{const.SPLUNK_PORT}/servicesNS/nobody/"
        f"{const.APP_NAME}/storage/passwords?output_mode=json&count=0"
    )

    try:
        response = _local_splunk_session().get(
            url,
            headers=headers,
            verify=False,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        entries = data.get("entry", [])
        return entries
    except Exception as e:
        logger.error("Failed to fetch storage passwords: %s", e)
        return []


def save_storage_password_value(
    splunk_session_token: str, key: str, value: str
) -> None:
    """Write (create or update) a value in Splunk's storage/passwords via REST."""
    base_url = f"https://{const.HOST}:{const.SPLUNK_PORT}/servicesNS/nobody/{const.APP_NAME}/storage/passwords"
    headers = {"Authorization": f"Splunk {splunk_session_token}"}
    password_id = f"{const.STORAGE_REALM}:{key}:"
    session = _local_splunk_session()

    # Try to delete the old entry first (ignore errors if it doesn't exist)
    try:
        session.delete(
            f"{base_url}/{password_id}",
            headers=headers,
            verify=False,
            timeout=10,
            params={"output_mode": "json"},
        )
    except Exception:
        pass

    # Create the new entry
    try:
        session.post(
            base_url,
            headers=headers,
            data={"name": key, "realm": const.STORAGE_REALM, "password": value},
            verify=False,
            timeout=10,
            params={"output_mode": "json"},
        )
        logger.debug("Saved storage password for key: %s", key)
    except Exception as e:
        logger.error("Failed to save storage password for key %s: %s", key, e)


def get_all_storage_values(entries: list) -> dict:
    """Extract all Flare config values from storage passwords in a single pass."""
    values: dict = {}
    for entry in entries:
        content = entry.get("content", {})
        if content.get("realm") == const.STORAGE_REALM:
            key = content.get("username")
            if key:
                values[key] = content.get("clear_password")
    return values
