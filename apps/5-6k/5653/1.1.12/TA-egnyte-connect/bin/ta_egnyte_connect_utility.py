import time
import requests
from modinput_wrapper.base_modinput import BaseModInput
from splunklib.binding import HTTPError, ResponseReader
import splunk.rest as rest


class TemporaryTokenError(Exception):
    """Raised when Egnyte token endpoint has a temporary failure (e.g., 5xx/429)
    and the current collection run should be skipped without deleting stored tokens.
    """

    def __init__(self, status_code, message):
        self.status_code = status_code
        super(TemporaryTokenError, self).__init__(message)


# HTTP status codes indicating truly transient Egnyte API failures.
# Only includes status codes that represent temporary conditions likely to resolve with retry:
#   429 - Too Many Requests: Rate limiting, will resolve after backoff
#   500 - Internal Server Error: Generic server error, often transient
#   502 - Bad Gateway: Upstream server issue, typically resolves quickly
#   503 - Service Unavailable: Server temporarily overloaded or in maintenance
#   504 - Gateway Timeout: Upstream timeout, often resolves on retry
#
# Excluded codes that represent permanent errors (won't resolve with retry):
#   501 (Not Implemented), 505 (HTTP Version Not Supported), 506 (Variant Also Negotiates),
#   507 (Insufficient Storage), 509 (Bandwidth Limit Exceeded), 510 (Not Extended),
#   511 (Network Authentication Required)
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def is_debug_enabled(helper):
    """Check if debug logging is enabled to avoid expensive computations."""
    return helper.get_log_level().upper() == 'DEBUG'


def validate_token_response(response_json, helper, session_id):
    """
    Validate that token response contains required fields.

    Args:
        response_json: Parsed JSON response from token endpoint
        helper: Helper object for logging
        session_id: Session ID for logging

    Returns:
        bool: True if response is valid, False otherwise
    """
    if not response_json:
        helper.log_error("Token response is empty. Session ID: {}".format(session_id))
        return False

    if not response_json.get("access_token"):
        helper.log_error("Token response missing access_token. Session ID: {}".format(session_id))
        return False

    return True


def generate_or_refresh_token(helper=None, auth_url=None, clientid=None, client_secret=None, code=None,
                              refresh_token=None, redirect_uri=None, session_id=None, scope=None):
    grant_type = "authorization_code" if code else "refresh_token"
    # Only format token generation details if debug logging is enabled
    if is_debug_enabled(helper):
        helper.log_debug("Starting token generation/refresh - grant_type: {}, auth_url: {}, scope: {}, session_id: {}"
                         .format(grant_type, auth_url, scope, session_id))

    if code:
        payload = {"client_id": clientid, "client_secret": client_secret, "grant_type": "authorization_code",
                   "redirect_uri": redirect_uri, "code": code}
        if scope:
            payload["scope"] = scope
    else:
        payload = {"client_id": clientid, "client_secret": client_secret, "grant_type": "refresh_token",
                   "redirect_uri": redirect_uri,
                   "refresh_token": refresh_token}
        if scope:
            payload["scope"] = scope

    # Log payload structure without sensitive data - only compute if debug logging is enabled
    if is_debug_enabled(helper):
        payload_debug = {k: v if k not in ['client_secret', 'code', 'refresh_token'] else '[REDACTED]' for k, v in
                         payload.items()}
        helper.log_debug("Token request payload structure: {}".format(payload_debug))

    response = requests.post(url=auth_url, data=payload, verify=True,
                             headers={"x-egnyte-splunk-session-id": session_id})
    helper.log_info("Generating token and response is there. Status Code: {}  x-egnyte-request-id: {}"
                    .format(response.status_code, response.headers['x-egnyte-request-id']))

    # Enhanced error logging for production troubleshooting - only compute if debug logging is enabled
    if response.status_code != 200:
        if is_debug_enabled(helper):
            helper.log_debug("Token generation failed - Status: {}, Response: {}, Headers: {}"
                             .format(response.status_code, response.text[:500], dict(response.headers)))

    return response


def generate_or_refresh_token_with_retry(helper=None, auth_url=None, clientid=None, client_secret=None,
                                         code=None, refresh_token=None, redirect_uri=None, session_id=None,
                                         scope=None, max_retries=3):
    """
    Generate or refresh OAuth token with retry logic and exponential backoff.

    Args:
        helper: Helper object for logging
        auth_url: OAuth token endpoint URL
        clientid: OAuth client ID
        client_secret: OAuth client secret
        code: Authorization code (for initial token generation)
        refresh_token: Refresh token (for token refresh)
        redirect_uri: OAuth redirect URI
        session_id: Session ID for logging
        scope: OAuth scope
        max_retries: Maximum number of retry attempts

    Returns:
        Response object from token request

    Raises:
        TemporaryTokenError: If all retries exhausted on retryable status codes (5xx, 429)
        requests.exceptions.RequestException: If all retries exhausted due to network errors
    """
    delay = 2  # Initial delay in seconds
    last_exception = None

    for attempt in range(max_retries):
        try:
            helper.log_info("Attempting token generation/refresh (attempt {}/{}). Session ID: {}"
                            .format(attempt + 1, max_retries, session_id))
            response = generate_or_refresh_token(
                helper=helper,
                auth_url=auth_url,
                clientid=clientid,
                client_secret=client_secret,
                code=code,
                refresh_token=refresh_token,
                redirect_uri=redirect_uri,
                session_id=session_id,
                scope=scope
            )

            # Retry on retryable HTTP statuses (if not last attempt)
            if response.status_code in RETRYABLE_STATUSES and attempt < max_retries - 1:
                helper.log_warning("Token endpoint returned status {}. Retrying in {} seconds. Session ID: {}"
                                   .format(response.status_code, delay, session_id))
                time.sleep(delay)
                delay = min(delay * 2, 30)  # Exponential backoff, max 30 seconds
                continue

            # Last attempt with retryable status - raise TemporaryTokenError
            if response.status_code in RETRYABLE_STATUSES:
                raise TemporaryTokenError(
                    response.status_code,
                    "Egnyte token endpoint returned {} after {} retries".format(response.status_code, max_retries)
                )

            # Non-retryable status: return response for validation by caller
            return response

        except requests.exceptions.RequestException as e:
            last_exception = e
            if attempt < max_retries - 1:
                helper.log_warning("Token request attempt {}/{} failed: {}. Retrying in {} seconds. Session ID: {}"
                                   .format(attempt + 1, max_retries, str(e), delay, session_id))
                time.sleep(delay)
                delay = min(delay * 2, 30)  # Exponential backoff, max 30 seconds
            else:
                helper.log_error("Token request failed after {} attempts. Last error: {}. Session ID: {}"
                                 .format(max_retries, str(e), session_id))

    # If we exhausted retries due to exceptions, raise the last exception
    raise last_exception


def get_token_from_secure_password(account_name, code, service, helper, checkpoint, checkpoint_for_input):
    storage_passwords = service.storage_passwords
    try:
        response = storage_passwords.get(account_name + "/" + code)
        reader: ResponseReader = ResponseReader(response["body"])

        xml_response_str: str = reader.read().decode("UTF-8")
        start_tag = "<s:key name=\"clear_password\">"
        end_tag = "</s:key>"
        # getting index of substrings
        idx1 = xml_response_str.index(start_tag)

        xml_data_substr = xml_response_str[idx1:]
        idx2_from_substring = xml_data_substr.index(end_tag)
        idx2 = idx1 + idx2_from_substring

        token: str = ''
        # getting elements in between
        for idx in range(idx1 + len(start_tag), idx2):
            token = token + xml_response_str[idx]

        # Only log if debug logging is enabled
        if is_debug_enabled(helper):
            helper.log_debug(
                "Access token in StoragePassword already exist. Erasing eventual access token from checkpoint.")
        checkpoint_for_input.pop("access_token", None)

        return token

    except HTTPError:
        # Only log if debug logging is enabled
        if is_debug_enabled(helper):
            helper.log_debug("Unable to find access token in StoragePassword engine. Performing one time "
                             "migration from checkpoint.")
        token = checkpoint.get('access_token')
        try:
            storage_passwords.create(token, account_name + "/" + code)
            # Only log if debug logging is enabled
            if is_debug_enabled(helper):
                helper.log_debug("Access token migrated.")
        except HTTPError:
            # Only log if debug logging is enabled
            if is_debug_enabled(helper):
                helper.log_debug("Access token already exist. Erasing access token from checkpoint.")
            checkpoint_for_input.pop("access_token", None)


def collect_issues(helper, access_token, data_url, params, session_id, max_retries=3):
    """
    Collect audit issues from Egnyte API with retry logic.

    Args:
        helper: Helper object for logging and HTTP requests
        access_token: OAuth access token
        data_url: Egnyte API endpoint URL
        params: Query parameters
        session_id: Session ID for logging
        max_retries: Maximum number of retry attempts

    Returns:
        tuple: (data, error) where data is the JSON response or None, error is error message or None

    Raises:
        TemporaryTokenError: If all retries exhausted on retryable status codes (5xx, 429)
    """
    if is_debug_enabled(helper):
        params_debug = dict(params)
        helper.log_debug("Starting data collection - URL: {}, params: {}, session_id: {}"
                         .format(data_url, params_debug, session_id))

    headers = {"Authorization": "Bearer " + str(access_token), "x-egnyte-splunk-session-id": session_id,
               "User-Agent": "Splunk-TA-Connect"}

    delay = 2  # Initial delay in seconds
    last_exception = None

    for attempt in range(max_retries):
        try:
            response_data = helper.send_http_request(data_url, "GET", parameters=params, payload=None,
                                                     headers=headers, cookies=None, verify=True, cert=None,
                                                     timeout=(10, 40), use_proxy=True)
            helper.log_info("Collecting data and response is there. Status Code: {}, x-egnyte-request-id: {}, "
                            "x-egnyte-splunk-session-id: {}"
                            .format(response_data.status_code,
                                    response_data.headers.get('x-egnyte-request-id', 'missing'),
                                    session_id))

            if response_data.status_code == 200:
                response_json = response_data.json()
                if is_debug_enabled(helper):
                    event_count = len(response_json.get("events", []))
                    has_more = response_json.get("moreEvents", False)
                    next_cursor = response_json.get("nextCursor", "None")
                    helper.log_debug("Data collection successful - Events: {}, MoreEvents: {}, NextCursor: {}"
                                     .format(event_count, has_more, next_cursor[:50] if next_cursor != "None" else "None"))
                return response_json, None

            # Retry on retryable HTTP statuses (if not last attempt)
            if response_data.status_code in RETRYABLE_STATUSES and attempt < max_retries - 1:
                helper.log_warning("Data collection returned status {}. Retrying in {} seconds (attempt {}/{}). Session ID: {}"
                                   .format(response_data.status_code, delay, attempt + 1, max_retries, session_id))
                time.sleep(delay)
                delay = min(delay * 2, 30)  # Exponential backoff, max 30 seconds
                continue

            # Last attempt with retryable status - raise TemporaryTokenError
            if response_data.status_code in RETRYABLE_STATUSES:
                helper.log_warning(
                    "Egnyte API returned {} during data collection after {} retries. Session ID: {}".format(
                        response_data.status_code, max_retries, session_id
                    )
                )
                raise TemporaryTokenError(
                    response_data.status_code,
                    "Egnyte API returned {} after {} retries - temporarily unavailable".format(
                        response_data.status_code, max_retries
                    )
                )

            # Other errors (non-retryable)
            error_msg = "Unexpected status ({}) while querying streaming API - message {}".format(
                response_data.status_code, response_data.text
            )
            if is_debug_enabled(helper):
                helper.log_debug("Data collection failed - Headers: {}, Full response: {}"
                                 .format(dict(response_data.headers), response_data.text[:1000]))
            return None, error_msg

        except requests.exceptions.RequestException as e:
            last_exception = e
            if attempt < max_retries - 1:
                helper.log_warning("Data collection attempt {}/{} failed: {}. Retrying in {} seconds. Session ID: {}"
                                   .format(attempt + 1, max_retries, str(e), delay, session_id))
                time.sleep(delay)
                delay = min(delay * 2, 30)  # Exponential backoff, max 30 seconds
            else:
                helper.log_error("Data collection failed after {} attempts. Last error: {}. Session ID: {}"
                                 .format(max_retries, str(e), session_id))

    # If we exhausted retries due to exceptions, wrap in TemporaryTokenError
    # so the caller can handle it gracefully (skip polling cycle)
    raise TemporaryTokenError(
        status_code=None,
        message="Network error after {} retries: {}".format(max_retries, str(last_exception))
    )


def send_ui_message(helper: BaseModInput, app_name: str, session_key: str, message: str) -> None:
    postargs = {
        'severity': "error",
        'name': app_name,
        'value': message
    }
    rest.simpleRequest('/services/messages', session_key, postargs=postargs)
