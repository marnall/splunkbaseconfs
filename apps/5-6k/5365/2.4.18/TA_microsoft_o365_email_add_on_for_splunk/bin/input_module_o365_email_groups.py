# encoding = utf-8

import json
import datetime
import splunk.entity
import urllib
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))


ACCESS_TOKEN = 'access_token'
TOKEN_CACHE = {}
DEFAULT_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


def get_token_cache_key(helper):
    account = helper.get_arg('global_account')
    return (
        helper.get_arg('endpoint'),
        helper.get_arg('tenant'),
        account['username'],
    )


def get_run_stats(helper):
    stats = getattr(helper, "_run_stats", None)
    if stats is None:
        stats = {
            "groups_seen": 0,
            "groups_emitted": 0,
            "members_seen": 0,
            "pages_fetched": 0,
            "retry_count": 0,
            "throttle_events": 0,
        }
        setattr(helper, "_run_stats", stats)
    return stats


def is_debug_enabled(helper):
    return bool(helper.get_arg('debug_mode'))


def build_log_context(helper, **extra):
    context = {
        "input": getattr(helper, "input_name", "o365_email_groups"),
        "tenant": helper.get_arg('tenant'),
        "endpoint": helper.get_arg('endpoint'),
    }
    for key, value in extra.items():
        if value not in (None, "", []):
            context[key] = value
    return context


def format_log_message(message, **context):
    if not context:
        return message
    ordered = ", ".join("{}={}".format(key, value) for key, value in sorted(context.items()))
    return "{} | {}".format(message, ordered)


def log_info(helper, message, **context):
    helper.log_info(format_log_message(message, **context))


def log_error(helper, message, **context):
    helper.log_error(format_log_message(message, **context))


def log_warning(helper, message, **context):
    helper.log_info(format_log_message("WARNING: " + message, **context))


def log_debug(helper, message, **context):
    helper.log_debug(format_log_message(message, **context))


def summarize_url(url):
    if "://" not in url:
        return url
    parts = url.split("://", 1)[1].split("/", 1)
    if len(parts) == 1:
        return "/"
    return "/" + parts[1]


def log_run_summary(helper, elapsed_seconds):
    stats = get_run_stats(helper)
    log_info(
        helper,
        "Run summary",
        **build_log_context(
            helper,
            elapsed_seconds=round(elapsed_seconds, 3),
            groups_seen=stats["groups_seen"],
            groups_emitted=stats["groups_emitted"],
            members_seen=stats["members_seen"],
            pages_fetched=stats["pages_fetched"],
            retries=stats["retry_count"],
            throttle_events=stats["throttle_events"],
        )
    )


def get_retry_after_seconds(response, attempt):
    retry_after_header = getattr(response, "headers", {}).get("Retry-After")
    if retry_after_header:
        try:
            return max(int(retry_after_header), 1)
        except ValueError:
            pass
    return min(2 ** attempt, 30)


def send_request_with_retry(
    helper,
    url,
    method,
    headers=None,
    parameters=None,
    payload=None,
    timeout=(15.0, 90.0),
    max_attempts=4,
):
    last_exception = None

    for attempt in range(max_attempts):
        if is_debug_enabled(helper):
            log_debug(helper, "Graph request", **build_log_context(helper, method=method, path=summarize_url(url), attempt=attempt + 1))
        try:
            response = helper.send_http_request(
                url,
                method,
                headers=headers,
                parameters=parameters,
                payload=payload,
                timeout=timeout,
            )
        except Exception as exc:
            last_exception = exc
            if attempt == max_attempts - 1:
                raise

            delay = min(2 ** attempt, 30)
            get_run_stats(helper)["retry_count"] += 1
            log_warning(
                helper,
                "Request failed; retrying",
                **build_log_context(helper, method=method, path=summarize_url(url), attempt=attempt + 1, max_attempts=max_attempts, retry_in_seconds=delay, error=str(exc))
            )
            time.sleep(delay)
            continue

        if is_debug_enabled(helper):
            log_debug(helper, "Graph response", **build_log_context(helper, method=method, path=summarize_url(url), attempt=attempt + 1, status_code=response.status_code))
        if response.status_code not in DEFAULT_RETRY_STATUS_CODES:
            return response

        if attempt == max_attempts - 1:
            return response

        delay = get_retry_after_seconds(response, attempt)
        stats = get_run_stats(helper)
        stats["retry_count"] += 1
        if response.status_code == 429:
            stats["throttle_events"] += 1
        log_warning(
            helper,
            "Received retryable response; retrying",
            **build_log_context(helper, method=method, path=summarize_url(url), attempt=attempt + 1, max_attempts=max_attempts, retry_in_seconds=delay, status_code=response.status_code)
        )
        time.sleep(delay)

    if last_exception:
        raise last_exception

    raise RuntimeError("Request failed without a response: {} {}".format(method, url))
#Obtain access token via oauth2
def _get_access_token(helper):
    
    if helper.get_arg('endpoint') == 'worldwide':
        login_url = 'https://login.microsoftonline.com/'
        graph_url = 'https://graph.microsoft.com/'
    elif helper.get_arg('endpoint') == 'gcchigh':
        login_url = 'https://login.microsoftonline.us/'
        graph_url = 'https://graph.microsoft.us/'
        
    cache_key = get_token_cache_key(helper)
    now = datetime.datetime.utcnow().timestamp()
    cached_token = TOKEN_CACHE.get(cache_key)

    if cached_token is None or now >= cached_token['expires_at']:
        _data = {
            'client_id': helper.get_arg('global_account')['username'],
            'scope': graph_url + '.default',
            'client_secret': helper.get_arg('global_account')['password'],
            'grant_type': 'client_credentials',
            'Content-Type': 'application/x-www-form-urlencoded'
            }
        _url = login_url + helper.get_arg('tenant') + '/oauth2/v2.0/token'
        if (sys.version_info > (3, 0)):
            access_token = send_request_with_retry(
                helper,
                _url,
                "POST",
                payload=urllib.parse.urlencode(_data),
                timeout=(15.0, 15.0),
            ).json()
        else:
            access_token = send_request_with_retry(
                helper,
                _url,
                "POST",
                payload=urllib.urlencode(_data),
                timeout=(15.0, 15.0),
            ).json()

        expires_in = int(access_token.get("expires_in", 3600))
        TOKEN_CACHE[cache_key] = {
            'token': access_token[ACCESS_TOKEN],
            'expires_at': now + max(expires_in - 60, 0),
        }
        return access_token[ACCESS_TOKEN]

    else:
        return cached_token['token']

#Returning version of TA
def _get_app_version(helper):
    app_version = ""
    if 'session_key' in helper.context_meta:
        session_key = helper.context_meta["session_key"]
        entity = splunk.entity.getEntity('/configs/conf-app','launcher', namespace=helper.get_app_name(), sessionKey=session_key, owner='nobody')
        app_version = entity.get('version')
    return app_version

#Setting minimum interval in TA to 600 seconds
def validate_input(helper, definition):
    interval_in_seconds = int(definition.parameters.get('interval'))
    if (interval_in_seconds < 600):
        raise ValueError("field 'Interval' shouldn't be lower than 10 minutes")
        
#Function to write events to Splunk
def _write_events(helper, ew, group_items=None):
    if group_items:
        event = helper.new_event(
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            data=json.dumps(group_items))
        ew.write_event(event)

#Function to check if returned url is secure
def is_https(url):
    if url.startswith("https://"):
        return True
    else:
        return False

#Main function for gathering groups.
def collect_events(helper, ew):
    start_time = time.time()
    get_run_stats(helper)
    
    if helper.get_arg('endpoint') == 'worldwide':
        graph_url = 'https://graph.microsoft.com/v1.0'
    elif helper.get_arg('endpoint') == 'gcchigh':
        graph_url = 'https://graph.microsoft.us/v1.0'
        
    access_token = _get_access_token(helper)

    headers = {"Authorization": "Bearer " + access_token,
                "User-Agent": "MicrosoftGraphEmail-Splunk/" + _get_app_version(helper)}

    if is_debug_enabled(helper):
        log_debug(helper, "Starting groups collection run", **build_log_context(helper, interval=helper.get_arg('interval')))

    endpoint = "/groups/"

    groups_response = send_request_with_retry(
        helper,
        graph_url + endpoint,
        "GET",
        headers=headers,
        parameters=None,
        timeout=(15.0, 90.0),
    ).json()
    
    group_ids = []
    stats = get_run_stats(helper)
    stats["pages_fetched"] += 1

    #Routine that iterates through the groups.  Uses the @odata.nextLink values to find the next endpoint to query.
    
    group_ids.append(groups_response['value'])
    
    while ("@odata.nextLink" in groups_response) and (is_https(groups_response["@odata.nextLink"])):
        nextlinkurl = groups_response["@odata.nextLink"]
        groups_response = send_request_with_retry(
            helper,
            nextlinkurl,
            "GET",
            headers=headers,
            parameters=None,
            timeout=(15.0, 90.0),
        ).json()
        group_ids.append(groups_response['value'])
        stats["pages_fetched"] += 1

    
    for group in group_ids:
        
        for item in group:

            group_items = {}

            group_items['group'] = item['mail']
            stats["groups_seen"] += 1

            group_id = item['id']

            endpoint = "/groups/" + group_id + "/members?$select=mail"

            members_response = send_request_with_retry(
                helper,
                graph_url + endpoint,
                "GET",
                headers=headers,
                parameters=None,
                timeout=(15.0, 90.0),
            ).json()

            emails = []

            while True:
                for item in members_response['value']:
                    if item['mail'] is not None:
                        emails.append(item['mail'])
                        stats["members_seen"] += 1

                if ("@odata.nextLink" in members_response) and is_https(members_response["@odata.nextLink"]):
                    members_response = send_request_with_retry(
                        helper,
                        members_response["@odata.nextLink"],
                        "GET",
                        headers=headers,
                        parameters=None,
                        timeout=(15.0, 90.0),
                    ).json()
                    stats["pages_fetched"] += 1
                else:
                    break

            group_items['members'] = emails

            _write_events(helper, ew, group_items)
            stats["groups_emitted"] += 1

            if is_debug_enabled(helper):
                log_debug(helper, "Emitted group snapshot", **build_log_context(helper, group=item.get('mail'), member_count=len(emails)))

    log_run_summary(helper, time.time() - start_time)
