import json
import uuid
from base64 import urlsafe_b64encode
from urllib.parse import urlparse, parse_qs, urlencode, ParseResult, urlunparse

import package_helper  # keep for added paths

def log_writer(logger, input_name, message, level, params):
    params["input_name"] = input_name
    params["message"] = message

    msg = " ".join([f'{k}="{v}"' for k, v in params.items()])

    log_levels = {
        "DEBUG": logger.debug,
        "ERROR": logger.error,
        "WARNING": logger.warning,
    }
    log_levels.get(level, logger.info)(msg)

def log_debug(logger, input_name, message, params={}):
    log_writer(logger, input_name, message, "DEBUG", params)

def log_info(logger, input_name, message):
    log_writer(logger, input_name, message, "INFO", {"status": "success"})

def log_error(logger, input_name, message, error, params={}):
    params["error"] = error
    params["status"] = "failed"

    log_writer(logger, input_name, message, "ERROR", params)

def log_warning(logger, input_name, message, params={}):
    log_writer(logger, input_name, message, "WARNING", params)

# Based on:
# - https://stash.atlassian.com/projects/CONFCLOUD/repos/confluence-frontend/browse/platform/packages/growth/origin-tracing
# - https://bitbucket.org/atlassian/java-origin-tracing/src/master/src/main/java/com/atlassian/growth/origin/tracing
def add_beacon_origin_tracing(original_url):
    if not original_url:
        return original_url

    # Generate base-64-encoded tracing object with random ID
    tracing_id = str(uuid.uuid4()).replace("-", "")
    tracing_object = {
        "i": tracing_id,
        "p": "beacon"
    }
    base64_encoded_tracing_object = urlsafe_b64encode(json.dumps(tracing_object).encode("utf-8"))

    # Build update URL
    parsed_url = urlparse(original_url)
    url_params = parse_qs(parsed_url.query)
    url_params["atlOrigin"] = base64_encoded_tracing_object
    return urlunparse(ParseResult(
        scheme=parsed_url.scheme,
        netloc=parsed_url.hostname,
        path=parsed_url.path,
        params=parsed_url.params,
        query=urlencode(url_params),
        fragment=parsed_url.fragment
    ))
