"""
Lovingly adapted from the original "alert_webhook" app which ships with Splunk.
"""

import json
import os
import sys
import traceback
from typing import Union
from urllib.parse import urlparse, quote

import requests
import splunk.rest  # type: ignore
from hmac_helper import get_hmac_headers
from oauth_helper import get_oauth_headers
from splunk.clilib import cli_common as cli  # type: ignore

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from loguru import logger

logger.remove()  # Remove default formatter
logger.add(sys.stderr, format="{level} {message}", level="DEBUG")


def get_credential(name: str, session_key: str):
    """
    Grab a specific credential from Splunk's credential store and JSON-decode it
    """
    # When invoked via | sendalert, users pass just the credential name (e.g. "my_cred").
    # When invoked via a saved alert, Splunk passes the full storage/passwords key
    # (e.g. "better_webhooks:my_cred:"). Normalize to the full key format either way.
    if not name.startswith("better_webhooks:"):
        name = f"better_webhooks:{name}:"
    url = f"/servicesNS/nobody/BetterWebhooks/storage/passwords/{quote(name, safe=':')}"

    server_response, server_content = splunk.rest.simpleRequest(
        url, getargs={"output_mode": "json"}, sessionKey=session_key
    )

    if server_response["status"] != "200":
        logger.error(
            "Error grabbing credential {}. Response from splunkd was {}",
            name,
            str(server_response),
        )
        raise Exception("Error grabbing credential from splunkd")

    # The server response is JSON-encoded
    credential = json.loads(server_content)["entry"][0]["content"]["clear_password"]

    # And so is the credential itself
    return json.loads(credential)

def send_webhook_request(
    url: str,
    body: bytes,
    headers: dict,
    auth: Union[tuple, None],
    user_agent: str,
    proxy: str,
):
    """
    Send the webhook and attempt to log as much information as possible if it fails.
    """
    if url is None:
        logger.error("No URL provided")
        return False

    if proxy:
        proxies = {
            "http": proxy,
            "https": proxy,
        }
    else:
        proxies = None

    if len(body) > 0:
        headers["Content-Type"] = "application/json"

    headers["User-Agent"] = user_agent
    logger.info(
        "Sending POST request to url={} with size={} bytes payload",
        url,
        len(body),
    )

    try:
        r = requests.post(url, data=body, headers=headers, auth=auth, proxies=proxies)
        logger.debug("Response body was {}", r.text)

        if 200 <= r.status_code < 300:
            logger.info("Webhook receiver responded with HTTP status={}, response body={}", r.status_code, r.text)
            return True
        else:
            logger.error("Webhook receiver responded with HTTP status={}, response body={}", r.status_code, r.text)
            return False

    except Exception:
        logger.error(
            "Unhandled exception when attempting to execute alert action. {}",
            traceback.format_exc(),
        )
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.error("Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
    try:
        settings = json.loads(sys.stdin.read())
        global_settings = cli.getConfStanza("better_webhooks", "settings")
        proxy = global_settings.get("proxy").strip()

        session_key = settings["session_key"]

        url = settings["configuration"].get("url")
        if url:
            parsed_url = urlparse(url)
            if parsed_url.scheme != "https":
                logger.error("URL scheme must be HTTPS")
                sys.exit(1)
        body_format = settings["configuration"].get("body_format")
        credential_name = settings["configuration"].get("credential")
        if credential_name == "None":
            credential_name = None

        if credential_name:
            credential = get_credential(credential_name, session_key=session_key)
        else:
            credential = None

        sid = settings.get("sid")
        search_name = settings.get("search_name")
        app = settings.get("app")
        owner = settings.get("owner")
        results_link = settings.get("results_link")
        result = settings.get("result")

        if body_format.strip() == "$none$":
            body = ""
        else:
            body = (
                body_format.replace("$sid$", json.dumps(sid))
                .replace("$search_name$", json.dumps(search_name))
                .replace("$app$", json.dumps(app))
                .replace("$owner$", json.dumps(owner))
                .replace("$results_link$", json.dumps(results_link))
                .replace("$full_result$", json.dumps(result))
            )

        logger.debug("Body: {}", repr(body))
        body = body.encode()

        if not credential:
            auth = None
            headers = {}
        elif credential["type"] == "basic":
            auth = (credential.get("username"), credential.get("password"))
            headers = {}
        elif credential["type"] == "header":
            auth = None
            headers = {
                credential.get("header_name").strip(): credential.get(
                    "header_value"
                ).strip()
            }
        elif credential["type"] == "hmac":
            auth = None
            hmac_secret = credential.get("hmac_secret")
            hmac_hash_function = credential.get("hmac_hash_function")
            hmac_digest_type = credential.get("hmac_digest_type")
            hmac_sig_header = credential.get("hmac_sig_header", "").strip()
            hmac_time_header = credential.get("hmac_time_header", "").strip()

            try:
                headers = get_hmac_headers(
                    body=body,
                    hmac_secret=hmac_secret,
                    hmac_hash_function=hmac_hash_function,
                    hmac_digest_type=hmac_digest_type,
                    hmac_sig_header=hmac_sig_header,
                    hmac_time_header=hmac_time_header,
                )
            except Exception:
                logger.error(
                    "Failed to compute HMAC signature, cannot send webhook. {}",
                    traceback.format_exc(),
                )
                sys.exit(2)
        elif credential["type"] == "oauth":
            auth = None
            oauth_client_id = credential.get("oauth_client_id")
            oauth_client_secret = credential.get("oauth_client_secret")
            oauth_token_url = credential.get("oauth_token_url", "").strip()
            oauth_scope = credential.get("oauth_scope", "").strip()

            try:
                headers = get_oauth_headers(
                    client_id=oauth_client_id,
                    client_secret=oauth_client_secret,
                    token_url=oauth_token_url,
                    scope=oauth_scope
                )
            except Exception:
                logger.error(
                    "Failed to obtain OAuth token, cannot send webhook. {}",
                    traceback.format_exc(),
                )
                sys.exit(2)
        else:
            logger.error("Unknown credential type: {}", credential["type"])
            sys.exit(2)

        user_agent = settings["configuration"].get("user_agent", "Splunk")
        if not send_webhook_request(
            url, body, headers, auth, user_agent=user_agent, proxy=proxy
        ):
            sys.exit(2)
    except Exception:
        logger.error(
            "Unhandled exception when attempting to execute alert action. {}",
            traceback.format_exc(),
        )
        sys.exit(3)
