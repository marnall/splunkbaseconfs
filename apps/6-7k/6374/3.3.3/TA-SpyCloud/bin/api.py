""" api.py

Python module for use with SpyCloud's Enterprise API

"""
import time
import requests
from splunktaucclib.rest_handler.endpoint import validator
import splunk.rest
import json
from urllib.parse import urlparse
from consts import USER_AGENT

def shouldRunOnThisSystem(helper):
    try:
        input_metadata = helper.context_meta
        session_key = input_metadata.get("session_key")
        
        # Get hostname of Searchhead
        inputs_path = "/services/server/info"
        
        response, content = splunk.rest.simpleRequest(
            inputs_path,
            method="GET",
            sessionKey=session_key,
            getargs={"output_mode": "json"}
        )
        
        content_json = json.loads(content)
        
        searchhead_hostname = content_json["entry"][0]["content"]["host"]
        helper.log_debug("searchhead_hostname = " + str(searchhead_hostname))
        
        searchhead_hostname = searchhead_hostname.split(".")[0]
        helper.log_debug("searchhead_hostname_split= " + str(searchhead_hostname))

        # Identify Captain or determine this SH is not in a cluster if status is not 200
        inputs_path = "/services/shcluster/captain/info"
         
        response, content = splunk.rest.simpleRequest(
            inputs_path,
            method="GET",
            sessionKey=session_key,
            getargs={"output_mode": "json"}
        )
        
        content_json = json.loads(content)
        
        localhost = False
        
        if response.status != 200:
            helper.log_info("status=spycloud_running Searchhead is not in a cluster")
            helper.log_debug("Searchhead is not in a clutster. Running SpyCloud Inputs on this search head. response.status=" + str(response.status) + " content=\"" + str(content) + "\"")
            return True
        
        else:
            captain_hostname = content_json["entry"][0]["id"]
            helper.log_debug("captain_hostname = " + str(captain_hostname))
            captain_hostname = urlparse(captain_hostname)
            helper.log_debug("captain_hostname_urlparse = " + str(captain_hostname))
            captain_hostname = captain_hostname.netloc.split(":")[0]
            helper.log_debug("captain_hostname_netlog_split = " + str(captain_hostname))
            
            if captain_hostname == "127.0.0.1" or captain_hostname == "localhost":
                localhost = True
            else:
                captain_hostname = captain_hostname.split(".")[0]
            
        if captain_hostname == searchhead_hostname or localhost == True:
            helper.log_debug("captain_hostname == searchhead_hostname. Running SpyCloud Inputs on this search head")
            helper.log_info("status=spycloud_running searchhead=" + searchhead_hostname)
            return True

        else:
            helper.log_debug("captain_hostname != searchhead_hostname. Not running SpyCloud Inputs on this search head")
            helper.log_info("status=spycloud_not_running searchhead=" + searchhead_hostname)
            return False
             
    except Exception as e:
        helper.log_error("Running SpyCloud in this searchhead due to error: " + str(e))
        helper.log_info("status=spycloud_running_by_default error=" + str(e))
        return True
    

def api_key_validator(value, data, *args, **kwargs):
    """ Test the API key by sending one request to breach catalog endpoint """
    import helpers
    from requests.exceptions import HTTPError, ProxyError, RequestException
    from splunktaucclib.rest_handler.endpoint.validator import ValidationFailed

    headers = {
        "User-Agent": USER_AGENT,
        "x-api-key": value,
    }
    url = "https://api.spycloud.io/enterprise-v2/breach/catalog?since=2017-01-01"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except ProxyError as e:
        error_msg = helpers.proxy_error_to_message(e)
        raise ValidationFailed(error_msg)
    except HTTPError as e:
        error_msg = helpers.http_error_to_message(e)
        raise ValidationFailed(error_msg)
    except RequestException as e:
        raise ValidationFailed(f"Connection Error: Unable to connect to SpyCloud API. Please check your internet connection and try again. Details: {str(e)}")
    except Exception as e:
        raise ValidationFailed(f"Unexpected Error: An unexpected error occurred while validating your API key. Please try again or contact support. Details: {str(e)}")

def make_headers(helper):
    api_key = helper.get_global_setting('spycloud_key')
    headers = {
        "User-Agent": USER_AGENT,  # Confirm USER_AGENT being used
        "x-api-key": api_key
    }
    helper.log_debug("headers=" + str(headers))
    return headers

def _send_with_retry(helper, url, method, headers, wait_duration):
    """Send an HTTP request via helper, retrying on 429 with exponential backoff.

    Returns (response, updated_wait_duration).
    Raises on non-429 errors or after max retries exhausted.
    """
    MAX_RETRIES = 3
    REQUEST_TIMEOUT_SECONDS = 60
    backoff = 10
    for attempt in range(1, MAX_RETRIES + 1):
        response = helper.send_http_request(
            url, method,
            parameters=None, payload=None,
            headers=headers, cookies=None,
            verify=True, cert=None,
            timeout=REQUEST_TIMEOUT_SECONDS, use_proxy=True,
        )
        if response.status_code != 429:
            response.raise_for_status()
            return response, wait_duration
        retry_after = response.headers.get("Retry-After")
        sleep_for = int(retry_after) if retry_after and retry_after.isdigit() else backoff
        helper.log_warning(
            f"rate_limited_429 url={url} attempt={attempt}/{MAX_RETRIES} "
            f"sleeping={sleep_for}s"
        )
        time.sleep(sleep_for)
        backoff = backoff * 2
        wait_duration = wait_duration * 2
    # Final attempt — let raise_for_status propagate the error
    response = helper.send_http_request(
        url, method,
        parameters=None, payload=None,
        headers=headers, cookies=None,
        verify=True, cert=None,
        timeout=REQUEST_TIMEOUT_SECONDS, use_proxy=True,
    )
    response.raise_for_status()
    return response, wait_duration


def breach_catalog(helper, since):
    """Generator function which yields SpyCloud breaches"""
    headers = make_headers(helper)
    cursor = ""
    wait_duration = 1.1
    method = "GET"
    while cursor is not None:
        url = "https://api.spycloud.io/enterprise-v2/breach/catalog?cursor={}&since={}".format(cursor, since)  # pylint: disable=consider-using-f-string,line-too-long
        helper.log_info("url=" + str(url))
        response, wait_duration = _send_with_retry(helper, url, method, headers, wait_duration)
        cursor = response.json()["cursor"]
        if cursor == "":
            cursor = None
        for result in response.json()["results"]:
            yield result
        time.sleep(wait_duration)

def watchlist(helper, since, until=None):
    """Generator function which iterates over watchlist and yields
    watchlist data for each"""
    headers = make_headers(helper)
    cursor = ""
    wait_duration = 1.1
    method = "GET"
    while True:
        # Build URL with optional since and until parameters
        url_parts = ["https://api.spycloud.io/enterprise-v2/breach/data/watchlist?"]
        params = []

        if since is not None:
            params.append(f"since={since}")

        if until is not None:
            params.append(f"until={until}")

        params.append(f"cursor={cursor}")
        url = url_parts[0] + "&".join(params)

        helper.log_info(f"url={url}")
        response, wait_duration = _send_with_retry(helper, url, method, headers, wait_duration)
        results = response.json()["results"]
        cursor = response.json()["cursor"]
        for result in results:
            yield result
        if not cursor or cursor == "":
            break
        time.sleep(wait_duration)

def modified_watchlist(helper, since_modification_date, until_modification_date=None):
    """Generator function which iterates over modified watchlist and yields
    watchlist data for each"""
    headers = make_headers(helper)
    cursor = ""
    wait_duration = 1.1
    method = "GET"
    while True:
        params = [f"since_modification_date={since_modification_date}"]
        if until_modification_date is not None:
            params.append(f"until_modification_date={until_modification_date}")
        params.append(f"cursor={cursor}")
        url = "https://api.spycloud.io/enterprise-v2/breach/data/watchlist?" + "&".join(params)
        helper.log_info(f"url={url}")
        response, wait_duration = _send_with_retry(helper, url, method, headers, wait_duration)
        results = response.json()["results"]
        cursor = response.json()["cursor"]
        for result in results:
            yield result
        if not cursor or cursor == "":
            break
        time.sleep(wait_duration)

def compass(helper, since, until=None):
    """Generator function which iterates over modified watchlist and yields
    watchlist data for each"""
    headers = make_headers(helper)
    cursor = ""
    wait_duration = 1.1
    method = "GET"
    while True:
        params = [f"since={since}"]
        if until is not None:
            params.append(f"until={until}")
        params.append(f"cursor={cursor}")
        url = "https://api.spycloud.io/enterprise-v2/compass/data?" + "&".join(params)
        helper.log_info("url=" + str(url))
        response, wait_duration = _send_with_retry(helper, url, method, headers, wait_duration)
        results = response.json()["results"]
        cursor = response.json()["cursor"]
        for result in results:
            yield result
        if not cursor or cursor == "":
            break
        time.sleep(wait_duration)

def identifiers(helper):
    """Generator function which iterates over identifiers and yields
    watchlist data for each"""
    headers = make_headers(helper)
    cursor = ""
    wait_duration = 1.1
    method = "GET"
    while True:
        url = "https://api.spycloud.io/enterprise-v2/watchlist/identifiers?cursor={}".format(cursor)  # pylint: disable=consider-using-f-string
        response, wait_duration = _send_with_retry(helper, url, method, headers, wait_duration)
        results = response.json()["results"]
        cursor = response.json()["cursor"]
        for result in results:
            yield result
        if not cursor or cursor == "":
            break
        time.sleep(wait_duration)
