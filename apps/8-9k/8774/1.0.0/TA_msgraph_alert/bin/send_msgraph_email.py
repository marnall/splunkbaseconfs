#!/usr/bin/env python3
import argparse
import json
import logging
import os
import re
import sys
from string import Template
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import splunk.entity as entity

APP_NAME = "TA_msgraph_alert"
LOG_NAME = "msgraph_send_email"
REALM = "msgraph"

USE_MOCK = False


# ---------------------------
# Logging
# ---------------------------
def setup_logger():
    logger = logging.getLogger(LOG_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    splunk_home = os.environ.get("SPLUNK_HOME", "")
    if splunk_home:
        log_dir = os.path.join(splunk_home, "var", "log", "splunk")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{LOG_NAME}.log")
        handler = logging.FileHandler(log_path)
    else:
        handler = logging.StreamHandler(sys.stderr)

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = setup_logger()


# ---------------------------
# Input handling
# ---------------------------
def read_json_from_stdin():
    return json.load(sys.stdin)


def read_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_config(payload):
    config = payload.get("configuration")
    if not isinstance(config, dict):
        raise RuntimeError("Missing or invalid 'configuration'")
    return config


def get_session_key(payload):
    session_key = payload.get("session_key")
    if not session_key:
        raise RuntimeError("Missing session_key in payload")
    return session_key


# ---------------------------
# Credentials 
# ---------------------------
def get_stored_credentials(session_key):
    entities = entity.getEntities(
        ["admin", "passwords"],
        namespace=APP_NAME,
        owner="nobody",
        sessionKey=session_key
    )

    for _, e in entities.items():
        if e.get("realm") == REALM and e.get("username") == "msgraph_credentials":
            return json.loads(e["clear_password"])

    raise RuntimeError("Stored credentials not found")


# ---------------------------
# Splunk result handling
# ---------------------------
def normalize_results(payload):
    for key in ("results", "result"):
        value = payload.get(key)
        if isinstance(value, list) and value:
            return value[0]
        if isinstance(value, dict):
            return value
    return {}


def flatten_payload_vars(payload, first_result):
    variables = {}

    for k, v in payload.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            variables[k] = "" if v is None else str(v)

    for k, v in first_result.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            variables[k] = "" if v is None else str(v)

    return variables


# ---------------------------
# Template rendering
# ---------------------------
_TOKEN_PATTERN = re.compile(r"\$([A-Za-z0-9_]+)\$")


def render_template(text, variables):
    if text is None:
        return ""
    converted = _TOKEN_PATTERN.sub(r"${\1}", str(text))
    return Template(converted).safe_substitute(variables)


# ---------------------------
# Helpers
# ---------------------------
def split_emails(value):
    return [x.strip() for x in str(value).split(",") if x.strip()]


# ---------------------------
# HTTP
# ---------------------------
def http_post_form(url, form_data):
    data = urlencode(form_data).encode("utf-8")
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    return http_request(req)


def http_post_json(url, json_data, headers=None):
    data = json.dumps(json_data).encode("utf-8")
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    return http_request(req)


def http_request(req):
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()}")
    except URLError as e:
        raise RuntimeError(f"Connection error: {e}")


# ---------------------------
# Auth
# ---------------------------
def acquire_token(tenant_id, client_id, client_secret):
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    status, body = http_post_form(url, {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    })

    if status != 200:
        raise RuntimeError(f"Token failed: {body}")

    return json.loads(body)["access_token"]


# ---------------------------
# Send email
# ---------------------------
def send_mail(token, sender_user, to_list, cc_list, subject, body, content_type):

    if USE_MOCK:
        logger.info("MOCK MODE - no external call")
        return

    endpoint = f"https://graph.microsoft.com/v1.0/users/{quote(sender_user)}/sendMail"

    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML" if content_type.upper() == "HTML" else "Text",
                "content": body
            },
            "toRecipients": [{"emailAddress": {"address": x}} for x in to_list]
        },
        "saveToSentItems": True
    }

    if cc_list:
        payload["message"]["ccRecipients"] = [
            {"emailAddress": {"address": x}} for x in cc_list
        ]

    status, _ = http_post_json(
        endpoint,
        payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    if status not in (200, 202):
        raise RuntimeError(f"Graph sendMail failed: {status}")


# ---------------------------
# Validation
# ---------------------------
def validate_required(config):
    required = ["to", "subject", "body"]
    missing = [k for k in required if not config.get(k)]
    if missing:
        raise RuntimeError(f"Missing required parameters: {', '.join(missing)}")


# ---------------------------
# Main
# ---------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--test-payload")
    args = parser.parse_args()

    payload = read_json_file(args.test_payload) if args.test_payload else read_json_from_stdin()

    session_key = get_session_key(payload)

    config = get_config(payload)
    validate_required(config)

    creds = get_stored_credentials(session_key)

    tenant_id = creds.get("tenant_id")
    client_id = creds.get("client_id")
    client_secret = creds.get("client_secret")
    sender_user = creds.get("sender_user")

    if not USE_MOCK:
        if not all([tenant_id, client_id, client_secret, sender_user]):
            raise RuntimeError("Missing authentication configuration")

    first_result = normalize_results(payload)
    variables = flatten_payload_vars(payload, first_result)

    to_list = split_emails(config.get("to"))
    cc_list = split_emails(config.get("cc"))

    subject = render_template(config.get("subject"), variables)
    body = render_template(config.get("body"), variables)
    content_type = config.get("content_type", "HTML")

    logger.info("Sending email to %s", to_list)

    token = None
    if not USE_MOCK:
        token = acquire_token(tenant_id, client_id, client_secret)

    send_mail(token, sender_user, to_list, cc_list, subject, body, content_type)

    logger.info("Email sent successfully")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        logger.exception("Alert action failed")
        print(str(e), file=sys.stderr)
        sys.exit(2)