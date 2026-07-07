"""
Copyright 2021 Intrinsec

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
from __future__ import print_function

from future.standard_library import install_aliases

install_aliases()

import json  # noqa
import logging  # noqa
import logging.handlers  # noqa
import os  # noqa
import sys  # noqa
import uuid  # noqa
from urllib.parse import urlparse  # noqa
from urllib.request import ProxyHandler, Request, build_opener, urlopen  # noqa

try:
    from splunk import setupSplunkLogger  # type: ignore # noqa
    from splunk.entity import getEntities  # type: ignore # noqa
except ImportError:
    pass


APP_NAME = "api_alerts"
PY2 = sys.version_info[0] == 2
HTTP_REQUEST_TIMEOUT = 60
SPLUNK_HOME = os.environ.get("SPLUNK_HOME", "/opt/splunk")


def get_header(session_key, header_name, logger):  # pragma: no cover
    try:
        # list all credentials/headers
        entities = getEntities(
            ["admin", "passwords"],
            namespace=APP_NAME,
            owner="nobody",
            sessionKey=session_key,
            count=-1,
        )
    except Exception as e:
        logger.error("Could not get stored headers from splunk. Error: {}".format(e))
        raise Exception(
            "Could not get %s stored headers from splunk. Error: %s"
            % (APP_NAME, str(e))
        )

    realm_headers = [h for _, h in entities.items() if h["realm"] == APP_NAME]

    # return first set of credentials
    header = next(
        (h for h in realm_headers if h["username"] == header_name),
        None,
    )
    if header is not None:
        return header["clear_password"]

    error = "No header {} has been found in realm {}, here are the available headers: {}".format(
        header_name, APP_NAME, ",".join(realm_headers)
    )
    logger.critical(error)
    raise Exception(error)


def encode(string, encodings=None):
    """From poetry project

    https://github.com/python-poetry/poetry/blob/master/poetry/utils/_compat.py#L218 # noqa: E501
    """
    if not PY2 and isinstance(string, bytes):
        return string

    if PY2 and isinstance(string, str):
        return string

    encodings = encodings or ["utf-8", "latin1", "ascii"]

    for encoding in encodings:
        try:
            return string.encode(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    return string.encode(encodings[0], errors="ignore")


def send_request(payload, alert_uuid, logger):
    settings = payload.get("configuration")
    # read session key sent from splunkd
    sessionKey = payload.get("session_key")

    url = settings.get("url")
    proxy = settings.get("proxy")
    header_name = settings.get("header")
    header_value = get_header(sessionKey, header_name, logger)

    headers = {}
    if header_value:
        headers["Authorization"] = header_value
    headers["Content-Type"] = "application/json"
    headers["X-Request-Id"] = alert_uuid

    data = json.dumps(
        {
            "search_name": payload.get("search_name"),
            "result": payload.get("result"),
            "search_query": settings.get("search_query"),
        }
    )
    encoded_data = encode(data)
    logger.info("Calling url='{}' with body='{}'".format(url, data))
    send_http_request(url, encoded_data, headers, logger, proxy)


def validate_url(url):
    """Check that URL is valid

    Check that the URL is in HTTPS
    and that it has a netloc and a path
    """

    validate_url = urlparse(url)
    if not all(
        [
            validate_url.scheme == "https",
            validate_url.netloc,
            validate_url.path,
        ]
    ):
        return False
    return True


def validate_proxy(url):
    """Check that proxy is valid

    Check that the proxy url is in http or https
    """
    validate_url = urlparse(url)
    if validate_url.scheme not in ["http", "https"]:
        return False
    return True


def send_http_request(url, encoded_data, headers, logger, proxy=None):
    if not validate_url(url):
        logger.critical("Configured URL {} is not a valid https URL".format(url))
        return

    req = Request(url, encoded_data, headers)
    opener = urlopen
    if proxy:
        if not validate_proxy(proxy):
            logger.critical("Configured URL {} is not a valid https URL".format(url))
            return
        handler = ProxyHandler({"https": proxy})
        opener = build_opener(handler).open

    try:
        # HTTPS scheme validated by validate_url function
        response = opener(req, timeout=HTTP_REQUEST_TIMEOUT)  # nosec
        logger.info("Received response HTTP status {}".format(response.code))

        if 200 <= response.code < 300:
            logger.info("HTTP request successfully sent")
        elif response.code in [401, 403]:
            logger.critical("Missing or invalid authentication token")
        else:
            logger.error("Failed to send http request: {}".format(response.msg))
    except Exception as e:
        logger.error("Error sending HTTP request to {}, got error {}".format(url, e))


def setup_logging(uuid):  # pragma: nocover
    logger = logging.getLogger("splunk.api_alerts")

    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log.cfg")
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log-local.cfg")
    LOGGING_STANZA_NAME = "python"
    LOGGING_FILE_NAME = "api_alerts.log"
    BASE_LOG_PATH = os.path.join("var", "log", "splunk")
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - {}: %(message)s".format(  # noqa
        uuid
    )
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode="a"
    )
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    setupSplunkLogger(
        logger,
        LOGGING_DEFAULT_CONFIG_FILE,
        LOGGING_LOCAL_CONFIG_FILE,
        LOGGING_STANZA_NAME,
    )
    return logger


def main():
    # Create an UUID in order to trace this alert through the entire pipeline
    alert_uuid = str(uuid.uuid4())
    logger = setup_logging(alert_uuid)

    if len(sys.argv) <= 1 or sys.argv[1] != "--execute":
        logger.critical("Unsupported execution mode (expected --execute flag)")
        sys.exit(1)

    payload = json.loads(sys.stdin.read())

    send_request(payload, alert_uuid, logger)


if __name__ == "__main__":
    main()
