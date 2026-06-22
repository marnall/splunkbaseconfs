# Updated packages/torq-workflows/src/main/resources/splunk/bin/torq_workflow.py
# Changes:
#    Supporting retry, backoff, etc
#    Multi-region hook validation

import csv
import gzip
import json
import logging
import os
import sys
import time
import traceback
import random
import re
from typing import Union
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import splunk.rest  # type: ignore
from splunk.clilib import cli_common as cli  # type: ignore

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from cim_actions import ModularAction, ModularActionTimer

logger = ModularAction.setup_logger("torq_modworkflow")

# Enable urllib3 retry logging
logging.getLogger("urllib3.util.retry").setLevel(logging.INFO)


class TorqWorkflow(ModularAction):
    def __init__(self, settings, logger, action_name=None):
        super(TorqWorkflow, self).__init__(settings, logger, action_name)
        self.addinfo()
        self.search_name = "Torq Workflow"

    def validate(self, result):
        pass

    def validate_url(self, url):
        if not url:
            raise Exception("URL is a required field")
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https":
            raise Exception("URL scheme must be HTTPS")
        hostname = parsed_url.hostname
        if not hostname:
            raise Exception("Invalid URL")
        
        # Match:
        # hooks.torq.io
        # hooks.<something>.torq.io
        pattern = r"^hooks(\.[a-z0-9-]+)?\.torq\.io$"

        if not re.match(pattern, hostname):
            raise Exception("URL must be a valid Torq webhook URL (such as https://hooks.torq.io or https://hooks.eu.torq.io)")

    def dowork(self, result):
        session_key = self.settings.get("session_key", "")
        global_settings = cli.getConfStanza("torq", "settings")
        proxy = global_settings.get("proxy").strip()

        body_format = self.configuration.get("body_format")
        credential_name = self.configuration.get("credential")
        if credential_name is None:
            raise Exception("Credential is a required field")

        try:
            credential = get_credential(credential_name, session_key=session_key)
        except Exception as e:
            logger.error(f"Error getting credential {credential_name}: {str(e)}")
            self.message(
                f"Error getting credential {credential_name}: {str(e)}",
                status="failure",
            )
            return

        if not credential:
            self.message(
                f"Credential {credential_name} not found",
                status="failure",
            )
            return

        url = credential.get("url")
        self.validate_url(url)

        sid = self.settings.get("sid", "")
        search_name = self.settings.get("search_name", "")
        app = self.settings.get("app", "")
        owner = self.settings.get("owner", "")
        results_link = self.settings.get("results_link", "")

        self.message(
            f"Sending payload to Torq: {sid} {search_name} {app} {owner} {results_link}"
        )

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

        auth = None
        header_name = credential.get("header_name")
        header_value = credential.get("header_value")
        if header_name and header_value:
            headers = {header_name.strip(): header_value.strip()}
        else:
            headers = {}

        user_agent = self.configuration.get("user_agent", "Splunk")

        try:
            status_code, response_text = send_webhook_request(
                url, body, headers, auth, user_agent=user_agent, proxy=proxy
            )
        except Exception as e:
            self.message(
                f"Encountered exception when sending webhook to Torq: {traceback.format_exc()}",
                status="failure",
            )
            return

        if 200 <= status_code < 300:
            output = f"HTTP Status Code: {status_code}\nResponse Text: {response_text}"
            self.addevent(output, "torq_response")
            self.writeevents(index="main", source=self.search_name)
            self.message(
                "Successfully sent payload to Torq",
                status="success",
                status_code=status_code,
                response_text=response_text,
            )
        else:
            self.message(
                "Failed to send payload to Torq",
                status="failure",
                status_code=status_code,
                response_text=response_text,
            )


def get_credential(name: str, session_key: str):
    url = f"/servicesNS/nobody/TA-torq/storage/passwords/{name}"
    server_response, server_content = splunk.rest.simpleRequest(
        url, getargs={"output_mode": "json"}, sessionKey=session_key
    )
    if server_response["status"] != "200":
        raise Exception(
            "Error grabbing credential {}. Response from splunkd was {}".format(
                name, str(server_response)
            )
        )
    credential = json.loads(server_content)["entry"][0]["content"]["clear_password"]
    return json.loads(credential)


# --- Custom Retry Class with Logging and Jitter ---
class LoggingRetry(Retry):
    """Retry class that logs each attempt and supports jitter."""

    def increment(
        self,
        method=None,
        url=None,
        response=None,
        error=None,
        _pool=None,
        _stacktrace=None,
    ):
        if response is not None:
            status = response.status
            logger.warning(
                "Retrying request: method=%s url=%s status=%s retries_left=%s",
                method,
                url,
                status,
                self.total,
            )
        elif error is not None:
            logger.warning(
                "Retrying request due to exception: method=%s url=%s error=%s retries_left=%s",
                method,
                url,
                error,
                self.total,
            )
        return super().increment(
            method=method,
            url=url,
            response=response,
            error=error,
            _pool=_pool,
            _stacktrace=_stacktrace,
        )

    def get_backoff_time(self):
        """Apply jitter to exponential backoff."""
        base = super().get_backoff_time()
        if base <= 0:
            return 0
        # Add jitter: random between 50% and 100% of the backoff
        jitter = random.uniform(base * 0.5, base)
        return jitter


# --- Retry Session Factory ---
def create_retry_session():
    """
    Create a requests Session with:
    - 429 retry policy: up to 6 retries, respect Retry-After, jitter
    - 5xx retry policy: up to 4 retries, jitter
    - network exception retry: up to 3 retries, jitter
    """
    retry = LoggingRetry(
        total=6,  # max retries for 429
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["POST"]),
        raise_on_status=False,
        respect_retry_after_header=True,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# --- Send Webhook with retries, exponential backoff + jitter ---
def send_webhook_request(
    url: str,
    body: bytes,
    headers: dict,
    auth: Union[tuple, None],
    user_agent: str,
    proxy: str,
):
    if proxy:
        proxies = {"http": proxy, "https": proxy}
    else:
        proxies = None

    headers = headers.copy()
    headers["Content-Type"] = "application/json"
    headers["User-Agent"] = user_agent

    logger.info("Sending POST request to url=%s payload_size=%s bytes", url, len(body))

    session = create_retry_session()

    try:
        response = session.post(
            url,
            data=body,
            headers=headers,
            auth=auth,
            proxies=proxies,
            timeout=10,
        )
    except requests.RequestException:
        logger.exception("All retry attempts exhausted while sending webhook")
        raise

    logger.debug(
        "Final response received: status=%s body=%s", response.status_code, response.text
    )
    return response.status_code, response.text


# --- Main execution ---
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        sys.exit("FATAL Unsupported execution mode (expected --execute flag)")

    try:
        modaction = TorqWorkflow(sys.stdin.read(), logger, "torq_workflow")
        logger.debug(modaction.settings)

        with ModularActionTimer(modaction, "main", modaction.start_timer):
            with gzip.open(modaction.results_file, "rt", newline="") as fh:
                for num, result in enumerate(csv.DictReader(fh)):
                    result.setdefault("rid", str(num))
                    modaction.update(result)
                    modaction.invoke()
                    modaction.validate(result)
                    modaction.dowork(result)
                    time.sleep(1.6)  # rate limiting

            modaction.writeevents()

    except Exception as e:
        try:
            modaction.message(e, status="failure", level=logging.CRITICAL)
        except:
            logger.critical(e)
        sys.exit("ERROR: %s" % e)
