# Copyright (C) 2023-2024 Splunk Inc. All Rights Reserved.

# Remote Search
"""
    Script helpers
"""

import json
import logging
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk import setupSplunkLogger, ResourceNotFound
import splunk.rest as rest
import requests

from soar_imports import REDIRECT_DETECTED_MSG


def setup_logging(
    log_file,
    logger_name,
    logger=None,
    level=logging.INFO,
    is_console_header=False,
    log_format="%(asctime)s %(levelname)s [%(name)s] [%(module)s] [%(funcName)s:%(lineno)d]  %(message)s",
    is_propagate=False,
):
    """
    Setup logging
    @param log_file: log file name
    @param logger_name: logger name (if logger specified then we ignore this argument)
    @param logger: logger object
    @param level: logging level
    @param is_console_header: set to true if console logging is required
    @param log_format: log message format
    @param is_propagate: set to true if you want to propagate log to higher level
    @return: logger
    """
    if log_file is None or logger_name is None:
        raise ValueError("log_file or logger_name is not specified")

    if logger is None:
        # Logger is singleton so if logger is already defined it will return old handler
        logger = logging.getLogger(logger_name)

    logger.propagate = is_propagate  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    # If handlers is already defined then do not create new handler, this way we can avoid file opening again
    # which is issue on windows see ITOA-2439 for more information
    if len(logger.handlers) == 0:
        file_handler = logging.handlers.RotatingFileHandler(
            make_splunkhome_path(["var", "log", "splunk", log_file]),
            maxBytes=2500000,
            backupCount=5,
        )
        formatter = logging.Formatter(log_format)
        file_handler.setFormatter(formatter)
        logger.handlers = []
        logger.addHandler(file_handler)

        # Console stream handler
        if is_console_header:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(log_format))
            logger.addHandler(console_handler)

    # Read logging level information from log.cfg so it will overwrite log
    # Note if logger level is specified on that file then it will overwrite log level
    LOGGING_DEFAULT_CONFIG_FILE = make_splunkhome_path(["etc", "log.cfg"])
    LOGGING_LOCAL_CONFIG_FILE = make_splunkhome_path(["etc", "log-local.cfg"])
    LOGGING_STANZA_NAME = "python"
    setupSplunkLogger(
        logger,
        LOGGING_DEFAULT_CONFIG_FILE,
        LOGGING_LOCAL_CONFIG_FILE,
        LOGGING_STANZA_NAME,
        verbose=False,
    )

    return logger


def rest_helper(helper, method, path, payload=None):
    if payload is None:
        payload = {}

    try:
        args = {"method": method, "sessionKey": helper.session_key}
        payload["output_mode"] = "json"
        if method == "POST" or method == "DELETE":
            args["postargs"] = payload
        else:
            args["getargs"] = payload
        response, contents = rest.simpleRequest(path, **args)
    except ResourceNotFound as e:
        # Not raising this error purposefully
        raise ResourceNotFound("ResourceNotFound: {}".format(str(e)))
    except Exception as e:
        helper.log.exception(e)
        raise e

    try:
        contents_json = json.loads(contents.decode("utf-8"))
    except Exception as e:
        helper.log.error(
            f"An exception occurred during deserialization of request response to {path}: {e}"
        )
        raise e
    return response, contents_json


def pretty_form_map(helper, form_data):
    try:
        return form_data[0][0]
    except Exception:
        return form_data


class RedirectDetectedException(Exception):
    pass


def make_request_and_handle_redirect_helper(
    helper, http_method, url, auth_headers, payload=None
):
    """
    Helper function for making requests and handling redirects. The entire
    logic of handling redirects should be encapsulated in this function.

    At this point, redirects are not allowed and will raise
    RedirectDetectedException. Handling such situations can be done by
    try-catching this exception.

    @param helper: Reference to the object using this function.
    @param http_method: HTTP method to use.
    @param url: URL to call.
    @param auth_headers: Authorization headers to use.
    @param payload: Data to send in the Request body.
    @return: Response object
    """
    response = requests.request(
        method=http_method,
        url=url,
        headers=auth_headers,
        verify=helper.verify_certs,
        proxies=helper.proxy,
        timeout=15,
        allow_redirects=helper.allow_redirects,
        data=payload,
    )
    if response.is_redirect:
        helper.log.debug(
            f"Status Code: {response.status_code}. Error: " f"{REDIRECT_DETECTED_MSG}"
        )
        raise RedirectDetectedException(REDIRECT_DETECTED_MSG)

    return response
