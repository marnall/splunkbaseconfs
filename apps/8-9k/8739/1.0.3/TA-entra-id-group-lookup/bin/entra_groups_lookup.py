#!/usr/bin/env python3
"""Splunk external lookup for Microsoft Entra ID user group membership."""

from __future__ import annotations

import configparser
import csv
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


APP_NAME = "TA-entra-id-group-lookup"
OUTPUT_FIELDS = [
    "entra_user",
    "group_id",
    "group_display_name",
    "group_mail",
    "group_security_enabled",
    "group_mail_enabled",
    "group_types",
    "group_membership_type",
    "error",
]


class LookupErrorWithMessage(Exception):
    """Expected lookup failure that should be returned in the error field."""


def app_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def read_config() -> configparser.SectionProxy:
    parser = configparser.ConfigParser()
    root = app_root()
    parser.read(
        [
            os.path.join(root, "default", "entra_id_lookup.conf"),
            os.path.join(root, "local", "entra_id_lookup.conf"),
        ]
    )
    if not parser.has_section("graph"):
        raise LookupErrorWithMessage("Missing [graph] stanza in entra_id_lookup.conf")
    return parser["graph"]


def clean_base_url(value: str) -> str:
    return value.strip().rstrip("/")


def required_setting(config: configparser.SectionProxy, name: str) -> str:
    value = config.get(name, fallback="").strip()
    if not value:
        raise LookupErrorWithMessage("Missing required graph.%s setting" % name)
    return value


def splunkd_uri() -> str:
    return os.environ.get("SPLUNKD_URI", "https://127.0.0.1:8089").rstrip("/")


def session_key_from_environment() -> str:
    candidates = (
        "SPLUNK_SESSION_KEY",
        "SPLUNKD_SESSION_KEY",
        "SESSION_KEY",
        "sessionKey",
    )
    for name in candidates:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def split_optional_splunk_header(payload: str) -> tuple[dict[str, str], str]:
    headers: dict[str, str] = {}
    lines = payload.splitlines(True)
    if not lines or ":" not in lines[0] or "," in lines[0].split(":", 1)[0]:
        return headers, payload

    body_start = 0
    for index, line in enumerate(lines):
        if line in ("\n", "\r\n"):
            body_start = index + 1
            break
        if ":" not in line:
            return {}, payload
        key, value = line.rstrip("\r\n").split(":", 1)
        headers[key] = value
    else:
        return headers, ""

    return headers, "".join(lines[body_start:])


def session_key_from_headers(headers: dict[str, str]) -> str:
    value = headers.get("sessionKey") or headers.get("authToken") or ""
    if value:
        return value.strip()
    auth_string = headers.get("authString", "")
    marker = "<authToken>"
    end_marker = "</authToken>"
    if marker in auth_string and end_marker in auth_string:
        return auth_string.split(marker, 1)[1].split(end_marker, 1)[0].strip()
    return ""


def session_key_from_context(headers: dict[str, str] | None = None) -> str:
    if headers:
        value = session_key_from_headers(headers)
        if value:
            return value
    return session_key_from_environment()


def request_json(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: int = 30,
    max_retries: int = 3,
) -> dict:
    headers = headers or {}
    attempt = 0
    while True:
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                if not body:
                    return {}
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                retry_after = exc.headers.get("Retry-After")
                sleep_seconds = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
                time.sleep(min(sleep_seconds, 30))
                attempt += 1
                continue
            raise LookupErrorWithMessage(format_http_error(exc.code, body))
        except urllib.error.URLError as exc:
            if attempt < max_retries:
                time.sleep(2**attempt)
                attempt += 1
                continue
            raise LookupErrorWithMessage("HTTP request failed: %s" % exc.reason)


def format_http_error(status_code: int, body: str) -> str:
    try:
        parsed = json.loads(body)
        message = parsed.get("error", {}).get("message")
        code = parsed.get("error", {}).get("code")
        if status_code == 403 and code == "Authorization_RequestDenied":
            return (
                "Graph HTTP 403 Authorization_RequestDenied: %s. "
                "Verify the Entra app registration has Microsoft Graph Application permission "
                "User.Read.All with admin consent; delegated User.Read is not used by client credentials."
            ) % (message or "Insufficient privileges to complete the operation")
        if code and message:
            return "Graph HTTP %s %s: %s" % (status_code, code, message)
        if message:
            return "Graph HTTP %s: %s" % (status_code, message)
    except json.JSONDecodeError:
        pass
    return "Graph HTTP %s: %s" % (status_code, body[:500])


def request_splunk_json(url: str, session_key: str, timeout: int = 30) -> dict:
    path = urllib.parse.urlparse(url).path
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    try:
        import splunk.rest as splunk_rest  # type: ignore

        _response, content = splunk_rest.simpleRequest(path, sessionKey=session_key, getargs=query)
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        return json.loads(content)
    except ImportError:
        pass

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": "Splunk %s" % session_key,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=None) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise LookupErrorWithMessage("Splunk password store HTTP %s: %s" % (exc.code, body[:500]))
    except urllib.error.URLError as exc:
        raise LookupErrorWithMessage("Unable to query Splunk password store: %s" % exc.reason)


def client_secret_from_storage_passwords(config: configparser.SectionProxy, headers: dict[str, str] | None = None) -> str:
    session_key = session_key_from_context(headers)
    if not session_key:
        return client_secret_from_passwords_conf(config)

    realm = config.get("secret_realm", fallback=APP_NAME).strip()
    name = config.get("secret_name", fallback="client_secret").strip()
    timeout = config.getint("timeout", fallback=30)
    query = urllib.parse.urlencode(
        {
            "output_mode": "json",
            "count": "0",
            "search": 'realm="%s" AND username="%s"' % (realm, name),
        }
    )
    url = "%s/servicesNS/nobody/%s/storage/passwords?%s" % (splunkd_uri(), APP_NAME, query)
    response = request_splunk_json(url, session_key, timeout=timeout)
    for entry in response.get("entry", []):
        content = entry.get("content", {})
        if content.get("realm") == realm and content.get("username") == name:
            secret = content.get("clear_password") or content.get("password")
            if secret:
                return secret
    raise LookupErrorWithMessage("Client secret not found in Splunk storage/passwords")


def client_secret_from_passwords_conf(config: configparser.SectionProxy) -> str:
    realm = config.get("secret_realm", fallback=APP_NAME).strip()
    name = config.get("secret_name", fallback="client_secret").strip()
    password_file = os.path.join(app_root(), "local", "passwords.conf")
    if not os.path.exists(password_file):
        raise LookupErrorWithMessage(
            "No Splunk session key available and local/passwords.conf does not exist; configure credentials in the setup page"
        )

    parser = configparser.ConfigParser()
    parser.read(password_file)
    stanza_names = [
        "credential:%s:%s:" % (realm, name),
        "credential:%s:%s" % (realm, name),
    ]
    encrypted_value = ""
    for stanza in stanza_names:
        if parser.has_section(stanza):
            encrypted_value = parser.get(stanza, "password", fallback="").strip()
            break
    if not encrypted_value:
        raise LookupErrorWithMessage("Client secret not found in local/passwords.conf")
    return decrypt_splunk_secret(encrypted_value)


def decrypt_splunk_secret(encrypted_value: str) -> str:
    try:
        from splunk.clilib import cli_common  # type: ignore

        secret = cli_common.decrypt(encrypted_value)
        if secret:
            return secret
    except Exception:
        pass

    splunk_home = os.environ.get("SPLUNK_HOME", "/opt/splunk")
    splunk_bin = os.path.join(splunk_home, "bin", "splunk")
    try:
        process = subprocess.run(
            [splunk_bin, "show-decrypted", "--value", encrypted_value],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        raise LookupErrorWithMessage("Unable to decrypt Splunk stored credential: %s" % exc)

    if process.returncode == 0 and process.stdout.strip():
        return process.stdout.strip().splitlines()[-1]
    message = process.stderr.strip() or process.stdout.strip() or "unknown decrypt failure"
    raise LookupErrorWithMessage("Unable to decrypt Splunk stored credential: %s" % message[:500])


def acquire_token(config: configparser.SectionProxy, headers: dict[str, str] | None = None) -> str:
    tenant_id = required_setting(config, "tenant_id")
    client_id = required_setting(config, "client_id")
    client_secret = client_secret_from_storage_passwords(config, headers=headers)
    authority_host = clean_base_url(config.get("authority_host", fallback="https://login.microsoftonline.com"))
    timeout = config.getint("timeout", fallback=30)
    max_retries = config.getint("max_retries", fallback=3)

    token_url = "%s/%s/oauth2/v2.0/token" % (authority_host, urllib.parse.quote(tenant_id, safe=""))
    form = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": clean_base_url(config.get("graph_host", fallback="https://graph.microsoft.com")) + "/.default",
            "grant_type": "client_credentials",
        }
    ).encode("utf-8")
    response = request_json(
        "POST",
        token_url,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=form,
        timeout=timeout,
        max_retries=max_retries,
    )
    token = response.get("access_token")
    if not token:
        raise LookupErrorWithMessage("Token endpoint response did not include access_token")
    return token


def membership_path(config: configparser.SectionProxy, user_value: str) -> str:
    membership_type = config.get("membership_type", fallback="transitive").strip().lower()
    if membership_type not in ("direct", "transitive"):
        raise LookupErrorWithMessage("graph.membership_type must be direct or transitive")
    relationship = "memberOf" if membership_type == "direct" else "transitiveMemberOf"
    encoded_user = urllib.parse.quote(user_value, safe="")
    return "/v1.0/users/%s/%s/microsoft.graph.group" % (encoded_user, relationship)


def fetch_groups(config: configparser.SectionProxy, token: str, user_value: str) -> list[dict]:
    graph_host = clean_base_url(config.get("graph_host", fallback="https://graph.microsoft.com"))
    timeout = config.getint("timeout", fallback=30)
    max_retries = config.getint("max_retries", fallback=3)
    select = "$select=id,displayName,mail,securityEnabled,mailEnabled,groupTypes"
    url = "%s%s?%s&$top=999" % (graph_host, membership_path(config, user_value), select)
    headers = {
        "Authorization": "Bearer %s" % token,
        "Accept": "application/json",
    }
    groups: list[dict] = []
    while url:
        response = request_json("GET", url, headers=headers, timeout=timeout, max_retries=max_retries)
        groups.extend(response.get("value", []))
        url = response.get("@odata.nextLink")
    return groups


def bool_text(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value).lower()


def group_row(user_value: str, group: dict, membership_type: str) -> dict[str, str]:
    return {
        "entra_user": user_value,
        "group_id": str(group.get("id") or ""),
        "group_display_name": str(group.get("displayName") or ""),
        "group_mail": str(group.get("mail") or ""),
        "group_security_enabled": bool_text(group.get("securityEnabled")),
        "group_mail_enabled": bool_text(group.get("mailEnabled")),
        "group_types": ";".join(group.get("groupTypes") or []),
        "group_membership_type": membership_type,
        "error": "",
    }


def error_row(input_row: dict[str, str], message: str) -> dict[str, str]:
    row = dict(input_row)
    for field in OUTPUT_FIELDS:
        row.setdefault(field, "")
    row["error"] = message
    return row


def empty_membership_row(user_value: str, membership_type: str) -> dict[str, str]:
    return {
        "entra_user": user_value,
        "group_id": "",
        "group_display_name": "",
        "group_mail": "",
        "group_security_enabled": "",
        "group_mail_enabled": "",
        "group_types": "",
        "group_membership_type": membership_type,
        "error": "",
    }


def main() -> int:
    headers, csv_payload = split_optional_splunk_header(sys.stdin.read())
    reader = csv.DictReader(csv_payload.splitlines())
    fieldnames = list(dict.fromkeys((reader.fieldnames or []) + OUTPUT_FIELDS))
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()

    try:
        config = read_config()
        membership_type = config.get("membership_type", fallback="transitive").strip().lower()
        token = acquire_token(config, headers=headers)
    except LookupErrorWithMessage as exc:
        for input_row in reader:
            writer.writerow(error_row(input_row, str(exc)))
        return 0

    for input_row in reader:
        user_value = (input_row.get("entra_user") or "").strip()
        if not user_value:
            writer.writerow(error_row(input_row, "Missing entra_user value"))
            continue
        try:
            groups = fetch_groups(config, token, user_value)
            if not groups:
                output = {field: input_row.get(field, "") for field in fieldnames}
                output.update(empty_membership_row(user_value, membership_type))
                writer.writerow(output)
                continue
            for group in groups:
                output = {field: input_row.get(field, "") for field in fieldnames}
                output.update(group_row(user_value, group, membership_type))
                writer.writerow(output)
        except LookupErrorWithMessage as exc:
            writer.writerow(error_row(input_row, str(exc)))

    return 0


if __name__ == "__main__":
    sys.exit(main())
