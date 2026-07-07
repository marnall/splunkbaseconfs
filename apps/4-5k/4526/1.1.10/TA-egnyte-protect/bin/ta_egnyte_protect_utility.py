import json
import sys
import time

import requests
import splunklib
from splunklib.binding import ResponseReader
import splunk.rest as rest


class TemporaryTokenError(Exception):
    """Raised when Egnyte token endpoint has a temporary failure (e.g., 5xx/429)
    and the current collection run should be skipped without deleting stored tokens.
    """

    def __init__(self, status_code, message):
        self.status_code = status_code
        super(TemporaryTokenError, self).__init__(message)


# HTTP status codes indicating temporary Egnyte API failures.
# This set aligns with the retry_statuses pattern used in cloudconnectlib/core/defaults.py
# for consistency across the codebase. These represent transient server errors that
# should trigger retry logic rather than permanent failures.
RETRYABLE_STATUSES = {429, 500, 501, 502, 503, 504, 505, 506, 507, 509, 510, 511}


def wait_for_storage_password_api(service, helper, max_retries=10, initial_delay=1):
    """
    Wait for StoragePassword API to be available with exponential backoff.

    Args:
        service: Splunk service object
        helper: Helper object for logging
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (will be doubled each retry)

    Returns:
        True if API is available, raises exception otherwise
    """
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            # Test if StoragePassword API is available by listing passwords
            service.storage_passwords.list(count=1)
            if attempt > 0:
                helper.log_info("StoragePassword API became available after {} attempts".format(attempt + 1))
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                helper.log_warning("StoragePassword API not ready (attempt {}/{}): {}. Retrying in {} seconds..."
                                   .format(attempt + 1, max_retries, str(e), delay))
                time.sleep(delay)
                delay = min(delay * 2, 30)  # Exponential backoff, max 30 seconds
            else:
                helper.log_error("StoragePassword API not available after {} retries. Last error: {}"
                                 .format(max_retries, str(e)))
                raise Exception("StoragePassword API unavailable after {} retries: {}".format(max_retries, str(e)))
    return False


def validate_token_response(response_dict, helper, session_id):
    """
    Validate OAuth token response contains all required fields.

    Args:
        response_dict: Dictionary containing OAuth response
        helper: Helper object for logging
        session_id: Session ID for logging

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["access_token", "refresh_token", "expires_in", "token_type"]
    missing_fields = [field for field in required_fields if field not in response_dict]

    if missing_fields:
        helper.log_error("OAuth response missing required fields: {}. Session ID: {}"
                         .format(missing_fields, session_id))
        return False

    # Validate field values are not None or empty
    if not response_dict.get("access_token"):
        helper.log_error("OAuth response has empty access_token. Session ID: {}".format(session_id))
        return False

    if not response_dict.get("refresh_token"):
        helper.log_error("OAuth response has empty refresh_token. Session ID: {}".format(session_id))
        return False

    # Validate expires_in is a valid number
    try:
        expires_in = float(response_dict.get("expires_in"))
        if expires_in <= 0:
            helper.log_error("OAuth response has invalid expires_in value: {}. Session ID: {}"
                             .format(expires_in, session_id))
            return False
    except (TypeError, ValueError) as e:
        helper.log_error("OAuth response expires_in is not a valid number: {}. Session ID: {}"
                         .format(response_dict.get("expires_in"), session_id))
        return False

    helper.log_debug("OAuth response validation successful. Session ID: {}".format(session_id))
    return True


def validate_stored_token_structure(token_structure, helper, session_id):
    """
    Validate stored token structure contains all required fields.

    Args:
        token_structure: Dictionary containing stored token data
        helper: Helper object for logging
        session_id: Session ID for logging

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["current_time", "expires_in", "refresh_token", "access_token"]
    missing_fields = [field for field in required_fields if field not in token_structure]

    if missing_fields:
        helper.log_warning("Stored token structure missing required fields: {}. Session ID: {}. Will regenerate token."
                           .format(missing_fields, session_id))
        return False

    # Validate expires_in can be converted to float
    try:
        float(token_structure.get("expires_in"))
    except (TypeError, ValueError):
        helper.log_warning("Stored token structure has invalid expires_in: {}. Session ID: {}. Will regenerate token."
                           .format(token_structure.get("expires_in"), session_id))
        return False

    # Validate current_time is a valid number
    try:
        float(token_structure.get("current_time"))
    except (TypeError, ValueError):
        helper.log_warning("Stored token structure has invalid current_time: {}. Session ID: {}. Will regenerate token."
                           .format(token_structure.get("current_time"), session_id))
        return False

    return True


def provide_token(helper=None, auth_url=None, clientid=None, client_secret=None, code=None, stanza_name=None,
                  refresh_token=None, app_name=None, service=None, session_key=None, session_id=None):
    """Provide a valid OAuth access token, refreshing if necessary.

    This function retrieves a stored token, validates it, refreshes if expired,
    or generates a new token from the auth code if needed.
    """
    storage_passwords = service.storage_passwords
    token = None

    # Key used to track one-time authorization code state per stanza. This is
    # used in the exception path to avoid repeatedly trying a known-invalid or
    # already-used authorization code.
    auth_code_state_key = None
    if stanza_name:
        auth_code_state_key = "egnyte_auth_code_state::{}".format(stanza_name)

    try:
        # Retrieve and parse stored token structure
        token_structure_str = get_token_from_secure_password(stanza_name, code, service, helper, session_id)
        token_structure = json.loads(token_structure_str)

        # Validate stored token structure
        if not validate_stored_token_structure(token_structure, helper, session_id):
            helper.log_warning("Stored token structure is invalid. Forcing regeneration. Session ID: {}"
                               .format(session_id))
            raise ValueError("Invalid stored token structure")

        # Check if token is expired
        token_validity = token_structure.get("current_time") + float(token_structure.get("expires_in"))
        if token_validity < time.time():
            helper.log_info("Access token expired. Refreshing token. Session ID: {}".format(session_id))
            # Token expired, need to refresh
            refresh_token_response = refresh_token_with_retry(
                helper,
                auth_url,
                clientid,
                client_secret,
                token_structure.get("refresh_token"),
                session_id,
            )

            status_code = refresh_token_response.status_code

            # Validate refresh response status code
            # Note: 5xx/429 already handled via TemporaryTokenError in refresh_token_with_retry
            if status_code != 200:
                helper.log_error(
                    "Refresh token failed with status {}. Response: {}. Session ID: {}".format(
                        status_code,
                        refresh_token_response.text[:500],
                        session_id,
                    )
                )

                # For non-retryable errors we delete the corrupted/invalid
                # token entry so that the next attempt can regenerate from the
                # auth code (subject to auth code state checks in the exception
                # handler below).
                try:
                    storage_passwords.delete(stanza_name + "/" + code)
                    helper.log_info("Deleted invalid token entry. Session ID: {}".format(session_id))
                except Exception as e:
                    helper.log_warning(
                        "Failed to delete invalid token entry: {}. Session ID: {}".format(
                            str(e),
                            session_id,
                        )
                    )

                # Force regeneration from auth code
                raise splunklib.binding.HTTPError(refresh_token_response, "Refresh token failed")

            response = refresh_token_response.json()

            # Validate refresh response contains required fields
            if not validate_token_response(response, helper, session_id):
                helper.log_error(
                    "Refresh token response validation failed. Deleting invalid token. Session ID: {}".format(
                        session_id
                    )
                )
                try:
                    storage_passwords.delete(stanza_name + "/" + code)
                except Exception as e:
                    helper.log_warning(
                        "Failed to delete invalid token entry: {}. Session ID: {}".format(
                            str(e),
                            session_id,
                        )
                    )
                raise ValueError("Invalid refresh token response")

            # Add current_time to response
            response.update({"current_time": time.time()})

            # Store refreshed token (delete old, create new)
            try:
                try:
                    storage_passwords.delete(stanza_name + "/" + code)
                except Exception as e:
                    helper.log_debug(
                        "No existing token entry to delete or delete failed: {}. Session ID: {}".format(
                            str(e),
                            session_id,
                        )
                    )
                storage_passwords.create(json.dumps(response), stanza_name + "/" + code)
                helper.log_info("Successfully refreshed and stored new token. Session ID: {}".format(session_id))
            except Exception as e:
                helper.log_error(
                    "Failed to store refreshed token: {}. Session ID: {}".format(
                        str(e),
                        session_id,
                    )
                )
                raise

            token = response.get("access_token")
        else:
            # Token still valid
            helper.log_debug("Using existing valid access token. Session ID: {}".format(session_id))
            token = token_structure.get("access_token")

    except (splunklib.binding.HTTPError, TypeError, ValueError, KeyError, json.JSONDecodeError) as e:
        """Handle token retrieval/validation failures by (carefully) falling back to auth code.

        This path is only taken when the stored token could not be used. We may
        attempt to generate a new token from the one-time authorization code,
        but only if we do not already know that the configured code is invalid
        or has been used.
        """
        helper.log_warning(
            "Token retrieval/validation failed: {} - {}. Generating new token from auth code. Session ID: {}".format(
                type(e).__name__,
                str(e),
                session_id,
            )
        )

        # Before trying to generate a new token, check whether the configured
        # authorization code is already known to be invalid or used. This
        # prevents us from hammering Egnyte with repeated calls using a
        # one-time code that cannot succeed.
        auth_state = {}
        if auth_code_state_key:
            try:
                auth_state = helper.get_check_point(auth_code_state_key) or {}
            except Exception as checkpoint_err:
                helper.log_warning(
                    "Failed to read auth code state checkpoint: {}. Session ID: {}".format(
                        str(checkpoint_err),
                        session_id,
                    )
                )
                auth_state = {}

            stored_code = auth_state.get("auth_code")
            code_status = auth_state.get("status", "unknown")

            if stored_code == code and code_status in ("invalid", "used"):
                error_payload = {
                    "error": "invalid_grant",
                    "error_description": (
                        "Configured authorization code is invalid or already used. "
                        "Please generate a new code in Egnyte and update the input."
                    ),
                }
                report_token_generation_error(
                    helper,
                    error_payload,
                    app_name,
                    rest,
                    session_key,
                    session_id,
                )
                sys.exit(1)

        generate_token_response = generate_token_with_retry(
            helper,
            auth_url,
            clientid,
            client_secret,
            code,
            session_id,
        )

        status_code = generate_token_response.status_code

        # Validate generation response status code
        # Note: 5xx/429 already handled via TemporaryTokenError in generate_token_with_retry
        if status_code != 200:
            helper.log_error(
                "Token generation failed with status {}. Response: {}. Session ID: {}".format(
                    status_code,
                    generate_token_response.text[:500],
                    session_id,
                )
            )

            try:
                generate_token_response_json = generate_token_response.json()
                if generate_token_response_json.get("error"):
                    if auth_code_state_key:
                        try:
                            helper.save_check_point(
                                auth_code_state_key,
                                {"auth_code": code, "status": "invalid"},
                            )
                        except Exception as checkpoint_err:
                            helper.log_warning(
                                "Failed to save auth code state checkpoint: {}. Session ID: {}".format(
                                    str(checkpoint_err),
                                    session_id,
                                )
                            )
                    report_token_generation_error(
                        helper,
                        generate_token_response_json,
                        app_name,
                        rest,
                        session_key,
                        session_id,
                    )
            except (json.JSONDecodeError, ValueError) as parse_err:
                helper.log_error(
                    "Token generation response is not valid JSON: {}. Response text: {}. Session ID: {}".format(
                        str(parse_err),
                        generate_token_response.text[:500],
                        session_id,
                    )
                )
            sys.exit(1)

        try:
            generate_token_response_json = generate_token_response.json()
        except (json.JSONDecodeError, ValueError) as parse_err:
            helper.log_error(
                "Token generation response is not valid JSON: {}. Response text: {}. Session ID: {}".format(
                    str(parse_err),
                    generate_token_response.text[:500],
                    session_id,
                )
            )
            sys.exit(1)

        if generate_token_response_json.get("error"):
            if auth_code_state_key:
                try:
                    helper.save_check_point(
                        auth_code_state_key,
                        {"auth_code": code, "status": "invalid"},
                    )
                except Exception as checkpoint_err:
                    helper.log_warning(
                        "Failed to save auth code state checkpoint: {}. Session ID: {}".format(
                            str(checkpoint_err),
                            session_id,
                        )
                    )
            report_token_generation_error(
                helper,
                generate_token_response_json,
                app_name,
                rest,
                session_key,
                session_id,
            )
            sys.exit(1)

        # Validate generated token response
        if not validate_token_response(generate_token_response_json, helper, session_id):
            helper.log_error("Generated token response validation failed. Session ID: {}".format(session_id))
            sys.exit(1)

        # Add current_time to response
        generate_token_response_json.update({"current_time": time.time()})

        # Store new token
        try:
            # Delete existing entry if present to avoid create conflicts
            try:
                storage_passwords.delete(stanza_name + "/" + code)
            except Exception as e:
                helper.log_debug(
                    "No existing token entry to delete or delete failed: {}. Session ID: {}".format(
                        str(e),
                        session_id,
                    )
                )

            try:
                storage_passwords.create(json.dumps(generate_token_response_json), stanza_name + "/" + code)
            except Exception as create_error:
                # If create fails (e.g., entry already exists due to race condition), try delete and recreate
                helper.log_warning(
                    "Create failed ({}), attempting delete and recreate. Session ID: {}".format(
                        str(create_error),
                        session_id,
                    )
                )
                try:
                    storage_passwords.delete(stanza_name + "/" + code)
                    storage_passwords.create(json.dumps(generate_token_response_json), stanza_name + "/" + code)
                    helper.log_info(
                        "Successfully recreated token entry after conflict. Session ID: {}".format(session_id)
                    )
                except Exception as retry_error:
                    helper.log_error(
                        "Failed to store token after retry: {}. Session ID: {}".format(
                            str(retry_error),
                            session_id,
                        )
                    )
                    raise

            helper.log_info("Successfully generated and stored new token. Session ID: {}".format(session_id))
        except Exception as e:
            helper.log_error(
                "Failed to store generated token: {}. Session ID: {}".format(
                    str(e),
                    session_id,
                )
            )
            sys.exit(1)

        # Mark the authorization code as used after a successful generation so
        # we know it should not be retried in the future.
        if auth_code_state_key:
            try:
                helper.save_check_point(
                    auth_code_state_key,
                    {"auth_code": code, "status": "used"},
                )
            except Exception as checkpoint_err:
                helper.log_debug(
                    "Failed to save auth code state checkpoint after successful generation: {}. Session ID: {}".format(
                        str(checkpoint_err),
                        session_id,
                    )
                )

        token = generate_token_response_json.get("access_token")

    if token is None:
        helper.log_error("Failed to obtain valid access token. Session ID: {}".format(session_id))
        sys.exit(1)
    else:
        return token

def get_token_from_secure_password(account_name, code, service, helper, session_id):
    """
    Retrieve token structure from Splunk StoragePassword.

    Args:
        account_name: Account/stanza name
        code: Authorization code
        service: Splunk service object
        helper: Helper object for logging
        session_id: Session ID for logging

    Returns:
        Token structure as JSON string
    """
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

        # Note: Stored data might have single quotes if stored as dict string representation
        # Convert to valid JSON with double quotes
        token_structure_str = token.replace("\'", "\"")

        # Validate it's valid JSON before returning
        try:
            json.loads(token_structure_str)
        except json.JSONDecodeError as e:
            helper.log_error("Stored token is not valid JSON: {}. Session ID: {}".format(str(e), session_id))
            raise

        return token_structure_str

    except Exception as e:
        helper.log_error("Failed to retrieve token from StoragePassword: {}. Session ID: {}"
                         .format(str(e), session_id))
        raise


def generate_token(helper, auth_url, clientid, client_secret, code, session_id):
    """
    Generate OAuth token from authorization code (single attempt).

    Args:
        helper: Helper object for logging
        auth_url: OAuth token endpoint URL
        clientid: OAuth client ID
        client_secret: OAuth client secret
        code: Authorization code
        session_id: Session ID for logging

    Returns:
        Response object from token generation request
    """
    payload = {"client_id": clientid, "client_secret": client_secret, "grant_type": "authorization_code",
               "no_redirect": "true", "code": code}

    try:
        response = requests.post(url=auth_url, data=payload, verify=True,
                                 headers={"x-egnyte-splunk-session-id": session_id}, timeout=30)
        helper.log_info("Generating token from code response status {}. Egnyte session id: {}"
                        .format(response.status_code, session_id))
        return response
    except requests.exceptions.RequestException as e:
        helper.log_error("Token generation request failed: {}. Session ID: {}".format(str(e), session_id))
        raise


def generate_token_with_retry(helper, auth_url, clientid, client_secret, code, session_id, max_retries=3):
    """
    Generate OAuth token from authorization code with retry logic and exponential backoff.

    Args:
        helper: Helper object for logging
        auth_url: OAuth token endpoint URL
        clientid: OAuth client ID
        client_secret: OAuth client secret
        code: Authorization code
        session_id: Session ID for logging
        max_retries: Maximum number of retry attempts

    Returns:
        Response object from token generation request

    Raises:
        TemporaryTokenError: If all retries exhausted on retryable status codes (5xx, 429)
        requests.exceptions.RequestException: If all retries exhausted due to network errors
    """
    delay = 2  # Initial delay in seconds
    last_exception = None

    for attempt in range(max_retries):
        try:
            helper.log_info("Attempting to generate token (attempt {}/{}). Session ID: {}"
                            .format(attempt + 1, max_retries, session_id))
            response = generate_token(helper, auth_url, clientid, client_secret, code, session_id)

            # Retry on retryable HTTP statuses (if not last attempt)
            if response.status_code in RETRYABLE_STATUSES and attempt < max_retries - 1:
                helper.log_warning("Token generation returned status {}. Retrying in {} seconds. Session ID: {}"
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
                helper.log_warning("Token generation attempt {}/{} failed: {}. Retrying in {} seconds. Session ID: {}"
                                   .format(attempt + 1, max_retries, str(e), delay, session_id))
                time.sleep(delay)
                delay = min(delay * 2, 30)  # Exponential backoff, max 30 seconds
            else:
                helper.log_error("Token generation failed after {} attempts. Last error: {}. Session ID: {}"
                                 .format(max_retries, str(e), session_id))

    # If we exhausted retries due to exceptions, wrap in TemporaryTokenError
    # so the caller can handle it gracefully (skip polling cycle)
    raise TemporaryTokenError(
        status_code=None,
        message="Network error after {} retries: {}".format(max_retries, str(last_exception))
    )


def report_token_generation_error(helper, response, app_name, rest, session_key, session_id):
    """
    Report token generation error to Splunk UI and logs.

    Args:
        helper: Helper object for logging
        response: Error response dictionary
        app_name: Application name
        rest: Splunk REST module
        session_key: Splunk session key
        session_id: Session ID for logging
    """
    helper.log_error("Error while getting access/refresh token error: {} error_description:{}. Egnyte session id: {}"
                     .format(response.get("error", ""), response.get("error_description", ""), session_id))
    helper.log_error("Please generate new code and update the input with new code.")
    postargs = {
        'severity': "error",
        'name': app_name,
        'value': "Egnyte Add-on: Please generate new code and update the input with new code."
    }
    try:
        rest.simpleRequest('/services/messages', session_key, postargs=postargs)
    except Exception as e:
        helper.log_error("Failed to send UI message: {}. Session ID: {}".format(str(e), session_id))
    return


def refresh_token(helper, auth_url, clientid, client_secret, refresh_token_value, session_id):
    """
    Refresh OAuth token using refresh token (single attempt).

    Args:
        helper: Helper object for logging
        auth_url: OAuth token endpoint URL
        clientid: OAuth client ID
        client_secret: OAuth client secret
        refresh_token_value: Refresh token value
        session_id: Session ID for logging

    Returns:
        Response object from token refresh request
    """
    payload = {"client_id": clientid, "client_secret": client_secret, "grant_type": "refresh_token",
               "no_redirect": "true", "refresh_token": refresh_token_value}

    try:
        response = requests.post(url=auth_url, data=payload, verify=True, timeout=30)
        helper.log_info("Refreshing token response status {}. Egnyte session id: {}".format(response.status_code,
                                                                                            session_id))
        return response
    except requests.exceptions.RequestException as e:
        helper.log_error("Token refresh request failed: {}. Session ID: {}".format(str(e), session_id))
        raise


def refresh_token_with_retry(helper, auth_url, clientid, client_secret, refresh_token_value, session_id, max_retries=3):
    """
    Refresh OAuth token using refresh token with retry logic and exponential backoff.

    Args:
        helper: Helper object for logging
        auth_url: OAuth token endpoint URL
        clientid: OAuth client ID
        client_secret: OAuth client secret
        refresh_token_value: Refresh token value
        session_id: Session ID for logging
        max_retries: Maximum number of retry attempts

    Returns:
        Response object from token refresh request

    Raises:
        TemporaryTokenError: If all retries exhausted on retryable status codes (5xx, 429)
        requests.exceptions.RequestException: If all retries exhausted due to network errors
    """
    delay = 2  # Initial delay in seconds
    last_exception = None

    for attempt in range(max_retries):
        try:
            helper.log_info("Attempting to refresh token (attempt {}/{}). Session ID: {}"
                            .format(attempt + 1, max_retries, session_id))
            response = refresh_token(helper, auth_url, clientid, client_secret, refresh_token_value, session_id)

            # Retry on retryable HTTP statuses (if not last attempt)
            if response.status_code in RETRYABLE_STATUSES and attempt < max_retries - 1:
                helper.log_warning("Token refresh returned status {}. Retrying in {} seconds. Session ID: {}"
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
                helper.log_warning("Token refresh attempt {}/{} failed: {}. Retrying in {} seconds. Session ID: {}"
                                   .format(attempt + 1, max_retries, str(e), delay, session_id))
                time.sleep(delay)
                delay = min(delay * 2, 30)  # Exponential backoff, max 30 seconds
            else:
                helper.log_error("Token refresh failed after {} attempts. Last error: {}. Session ID: {}"
                                 .format(max_retries, str(e), session_id))

    # If we exhausted retries due to exceptions, wrap in TemporaryTokenError
    # so the caller can handle it gracefully (skip polling cycle)
    raise TemporaryTokenError(
        status_code=None,
        message="Network error after {} retries: {}".format(max_retries, str(last_exception))
    )


def collect_issues(helper, access_token, data_url, session_id):
    headers = {"Authorization": "Bearer " + str(access_token), "x-egnyte-splunk-session-id": session_id,
               "User-Agent": "Splunk-TA-SnG"}
    response_data = helper.send_http_request(
        data_url,
        "GET",
        parameters=None,
        payload=None,
        headers=headers,
        cookies=None,
        verify=True,
        cert=None,
        timeout=(10, 40),
        use_proxy=False,
    )
    helper.log_info(
        "Collecting data and response is there. Status Code: {}, x-egnyte-request-id: {}, "
        "x-egnyte-splunk-session-id: {}".format(
            response_data.status_code,
            response_data.headers.get("x-egnyte-request-id", "missing header"),
            session_id,
        )
    )

    # Successful response – parse JSON safely.
    if response_data.status_code == 200:
        try:
            return response_data.json()
        except (ValueError, json.JSONDecodeError) as e:
            helper.log_error(
                "Egnyte API returned non-JSON body with 200 status while collecting issues. Error: {}. "
                "Session ID: {}".format(
                    str(e),
                    session_id,
                )
            )
            # Return None for consistency with other error cases, allowing caller
            # to skip this polling cycle gracefully instead of crashing.
            return None

    # Token expired/invalid – caller will handle and surface re-auth requirement.
    if response_data.status_code == 401:
        return response_data.status_code

    # Any other status is treated as a temporary or unexpected error. We log the
    # details and return None so the caller can skip this polling cycle without
    # crashing on JSONDecodeError.
    helper.log_error(
        "Egnyte API returned error while collecting issues. Status: {} Body (first 500 chars): {} "
        "Session ID: {}".format(
            response_data.status_code,
            response_data.text[:500],
            session_id,
        )
    )
    return None
