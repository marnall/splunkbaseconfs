import json
from datetime import datetime, timedelta, timezone
import requests
import re
import base64
from time import sleep
import platform

__format_Date = "%Y-%m-%dT%H:%M:%SZ"
__COMPANY_NAME = "oodrive"
__APP_NAME = "splunk_oodrive_workspace_tracking"
__APP_VERSION = "1.7.0"

def validate_input(helper, definition):
    pass

def read_config(helper, ew):
    configs = {}
    configs["client_id"] = helper.get_arg("client_id")
    configs["domain_url"] = helper.get_arg("domain_url")
    configs["client_secret"] = helper.get_arg("client_secret")
    configs["workspace_name"] = helper.get_arg("workspace_name")
    configs["refresh_token"] = helper.get_arg("refresh_token")
    configs["old_refresh_token"] = helper.get_check_point(
        f'old_refresh_token-{configs["workspace_name"]}-{configs["domain_url"]}'
    )
    configs["enable_app_messages"] = helper.get_arg("enable_app_messages")
    configs["start_page"] = 0
    configs["max_page"] = 10
    configs["page_size"] = 50
    configs["retries"] = 3
    configs["request_timeout"] = 20
    configs["previous_query_date_iso_utc"] = helper.get_check_point(
        f'previous_query_date_iso_utc-{configs["workspace_name"]}-{configs["domain_url"]}'
    )
    configs["time_delta_minute"] = 1
    configs["proxies"] = {}

    if helper.get_proxy():
        configs["proxy_host"] = helper.get_proxy().get("proxy_url")
        configs["proxy_port"] = helper.get_proxy().get("proxy_port")
        configs["proxy_username"] = helper.get_proxy().get("proxy_username")
        configs["proxy_password"] = helper.get_proxy().get("proxy_password")
        configs["proxies"] = set_user_defined_proxy(configs)
    else:
        configs["proxies"] = {}

    configs["user_agent"] = build_user_agent()

    return configs


def set_user_defined_proxy(config_params):
    proxy_host = config_params["proxy_host"]
    proxy_port = config_params["proxy_port"]
    proxy_username = config_params["proxy_username"]
    proxy_password = config_params["proxy_password"]

    protocol = "https" if proxy_host.startswith("https") else "http"

    proxy_host = re.sub(r"^https?://", "", proxy_host)

    proxy_url = f"{proxy_host}:{proxy_port}" if proxy_port else proxy_host
    if proxy_username and proxy_password:
        proxy_url = f"{proxy_username}:{proxy_password}@{proxy_url}"

    proxies = {
        "https": f"{protocol}://{proxy_url}"
    }
    return proxies


def build_user_agent():
    try:
        python_version = platform.python_version()
        os_info = platform.system() + "/" + platform.release()
        
        return f"{__COMPANY_NAME}/{__APP_VERSION} ({__APP_NAME}; {os_info}; Python/{python_version};)"

    except Exception as e:
        return f"{__COMPANY_NAME}/{__APP_VERSION} (({__APP_NAME}; error-building-ua)"  


splunk_health_check_done = True


def collect_events(helper, ew):
    global splunk_health_check_done

    helper.log_debug("collect_events")

    config_params = read_config(helper, ew)
    if config_params is None:
        return
    
    user_refresh_token = config_params["refresh_token"]
    old_user_refresh_token = config_params["old_refresh_token"]
    
    if user_refresh_token != old_user_refresh_token:
        helper.save_check_point(
            f'refresh_token-{config_params["workspace_name"]}-{config_params["domain_url"]}',
            user_refresh_token,
        )
        helper.save_check_point(
            f'old_refresh_token-{config_params["workspace_name"]}-{config_params["domain_url"]}',
            user_refresh_token,
        )
        helper.save_check_point(
            f'access_token-{config_params["workspace_name"]}-{config_params["domain_url"]}',
            "",
        )

    domain_url = config_params["domain_url"]

    def health_check_func(cfg, health_url):
        return httpClient_get_url(cfg, health_url, helper=helper, ew=ew, use_access_token=False)

    def monitoring_func(cfg, monitoring_url):
        return httpClient_get_url(cfg, monitoring_url, helper=helper, ew=ew, use_access_token=True)

    def export_func(events):
        for raw_event in events:
            event = helper.new_event(
                data=json.dumps(raw_event),
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype(),
            )
            ew.write_event(event)

    def log_func(log_level, message, _=None):
        if config_params["enable_app_messages"]:
            if isinstance(message, dict) and "message" in message:
                data_str = message["message"]
            else:
                data_str = str(message)

            event = helper.new_event(
                data=data_str,
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype() + "-debug",
            )
            ew.write_event(event)

    collect_paginated_events(
        helper,
        config_params=config_params,
        domain_url=domain_url,
        health_check_func=health_check_func,
        monitoring_func=monitoring_func,
        log_func=log_func,
        export_func=export_func,
        skip_health_check=splunk_health_check_done,
    )

    if not splunk_health_check_done:
        splunk_health_check_done = True


def httpClient_get_url(config_params, url: str, helper, ew, use_access_token: bool = True):

    def log_func(log_level, message, _=None):
        if config_params["enable_app_messages"]:
            if isinstance(message, dict) and "message" in message:
                data_str = message["message"]
            else:
                data_str = str(message)

            event = helper.new_event(
                data=data_str,
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype() + "-debug",
            )
            ew.write_event(event)

    access_token = None
    if use_access_token:
        access_token = helper.get_check_point(
            f'access_token-{config_params["workspace_name"]}-{config_params["domain_url"]}'
        )

    def do_request():
        return perform_http_request(
            config_params=config_params,
            url=url,
            refresh_access_token_func=httpClient_refresh_access_token,
            log_func=log_func,
            helper=helper,
            ew=ew,
            access_token=access_token,
        )

    return retry_request(
        request_func=do_request,
        max_retries=int(config_params.get("retries", 3)),
        retry_delay=2,
        log_retry=log_func,
    )


def httpClient_refresh_access_token(config_params, helper, ew):
    try:
        refresh_token = helper.get_check_point(
            f'refresh_token-{config_params["workspace_name"]}-{config_params["domain_url"]}'
        )

        if not refresh_token:
            refresh_token = config_params["refresh_token"]

        def log_retry(log_level, message, _=None):
            if config_params["enable_app_messages"]:
                if isinstance(message, dict) and "message" in message:
                    data_str = message["message"]
                else:
                    data_str = str(message)

                event = helper.new_event(
                    data=data_str,
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype() + "-debug",
                )
                ew.write_event(event)

        result = perform_token_refresh(
            refresh_token=refresh_token,
            config_params=config_params,
            retry_delay=2,
            log_retry=log_retry,
            log_failure=None,
        )

        if result is None:
            if config_params["enable_app_messages"]:
                event = helper.new_event(
                    data="Failed to obtain a new access token after retries.",
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype() + "-debug",
                )
                ew.write_event(event)
            raise requests.HTTPError("Failed to obtain a new access token after retries.")

        access_token = result["access_token"]
        new_refresh_token = result["refresh_token"]

        if new_refresh_token:
            helper.save_check_point(
                f'refresh_token-{config_params["workspace_name"]}-{config_params["domain_url"]}',
                new_refresh_token,
            )

        if access_token:
            helper.save_check_point(
                f'access_token-{config_params["workspace_name"]}-{config_params["domain_url"]}',
                access_token,
            )

        return access_token

    except requests.HTTPError:
        return None


def perform_token_refresh(refresh_token, config_params, retry_delay=2, log_retry=None, log_failure=None):

    def make_request():
        client_id = config_params["client_id"]
        client_secret = config_params["client_secret"]
        domain_url = config_params["domain_url"]
        workspace_name = config_params["workspace_name"]
        request_timeout = int(config_params["request_timeout"])
        proxies = config_params["proxies"]
        user_agent = config_params["user_agent"]

        credentials = f"{client_id}:{client_secret}"
        base64_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

        authorization_header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Client-Id": client_id,
            "Authorization": f"Basic {base64_credentials}",
            "User-Agent": user_agent,
        }

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "workspace": workspace_name,
        }

        oauth_url = f"https://{domain_url}/auth/oauth/token"
        response = requests.post(
            oauth_url,
            headers=authorization_header,
            data=payload,
            timeout=request_timeout,
            proxies=proxies,
        )
        response.raise_for_status()

        response_json = response.json()
        return {
            "access_token": response_json.get("access_token"),
            "refresh_token": response_json.get("refresh_token"),
        }

    retries = int(config_params.get("retries", 3))
    return retry_request(
        request_func=make_request,
        max_retries=retries,
        retry_delay=retry_delay,
        log_retry=log_retry,
        log_failure=log_failure,
    )


def perform_http_request(config_params, url, refresh_access_token_func, log_func, helper, ew, access_token=None):

    client_id = config_params["client_id"]
    proxies = config_params["proxies"]
    user_agent = config_params["user_agent"]

    authorization_header = {
        "Content-Type": "application/json",
        "X-Client-Id": client_id,
        "Accept-Language": "en",
        "X-Accept-Version": "1.0.0",
        "User-Agent": user_agent,
    }
    if access_token:
        authorization_header["Authorization"] = f"Bearer {access_token}"

    request_timeout = int(config_params["request_timeout"])
    response = requests.get(
        url,
        headers=authorization_header,
        timeout=request_timeout,
        proxies=proxies
    )

    if response.status_code in [500, 403, 401, 503]:
        log_func("warning", "Bearer token expired. Renewing authentication...")
        new_access_token = refresh_access_token_func(config_params, helper, ew)
        if new_access_token is not None:
            log_func("info", {"message": "Successfully obtained a new bearer token."})
            authorization_header["Authorization"] = f"Bearer {new_access_token}"
            response = requests.get(
                url,
                headers=authorization_header,
                timeout=request_timeout,
                proxies=proxies
            )

    if 200 <= response.status_code < 300:
        log_func("info", {"message": f"Successful query to {url}"})
        return response.json()
    else:
        response.raise_for_status()
        return None


def retry_request(request_func, max_retries, retry_delay=2, log_retry=None, log_failure=None, *args, **kwargs):
    attempts = 0
    while attempts < max_retries:
        try:
            return request_func(*args, **kwargs)
        except requests.RequestException as e:
            if log_retry:
                log_retry("warning", {"message": f"Attempt {attempts + 1} of {max_retries} due to error: {e}"})
            if attempts < max_retries - 1:
                sleep(retry_delay)
            else:
                if log_failure:
                    log_failure("error", {"message": f"Failed after {max_retries} retries: {e}"})
                return None
        attempts += 1


def collect_paginated_events(
        helper,
        config_params,
        domain_url,
        health_check_func=None,
        monitoring_func=None,
        log_func=None,
        export_func=None,
        skip_health_check=False,
):
    iso_date_utc = datetime.now(timezone.utc)
    current_iso_date_utc = iso_date_utc.strftime(__format_Date)

    query_date_iso_utc = helper.get_check_point(
        f'previous_query_date_iso_utc-{config_params["workspace_name"]}-{config_params["domain_url"]}'
    )
    time_delta_minute = config_params["time_delta_minute"]

    if not skip_health_check:
        health_url = f"https://{domain_url}/tracking/manage/health"
        while True:
            try:
                health_response = health_check_func(config_params, health_url)
                if health_response is None:
                    log_func("error", {
                        "message": "Failed to reach the health check endpoint after all retries. "
                                   "Please check the network connection and Application Health."
                    })
                    continue

                health_status = health_response.get("status", "").upper()
                if health_status not in ["UP", "WARN"]:
                    log_func("error", {
                        "message": "Failed to reach the health check endpoint after all retries. "
                                   "Please check the network connection and Application Health."
                    })
                    continue

                log_func("info", {"message": "Network health check successful. Endpoint is reachable."})
                break

            except Exception as e:
                log_func("error", {"message": f"Exception during health check: {str(e)}"})
                continue

    if not query_date_iso_utc or query_date_iso_utc == "":
        previous_query_date_iso_utc = iso_date_utc - timedelta(minutes=time_delta_minute)
        query_date_iso_utc = previous_query_date_iso_utc.strftime(__format_Date)

    start_page = int(config_params.get("start_page", 0))
    max_page = int(config_params.get("max_page", 10))
    page_size = int(config_params.get("page_size", 50))

    all_events = []

    for page in range(start_page, max_page):
        monitoring_url = (
            f"https://{domain_url}/tracking/api/monitoring/"
            f'{config_params["workspace_name"]}?startDate={query_date_iso_utc}&page={page}&size={page_size}'
        )

        try:
            monitoring_data = monitoring_func(config_params, monitoring_url)
            if monitoring_data:
                helper.save_check_point(
                    f'previous_query_date_iso_utc-{config_params["workspace_name"]}-{config_params["domain_url"]}',
                    current_iso_date_utc
                )

                events = monitoring_data.get("content", [])
                all_events.extend(events)

                if events:
                    export_func(events)

                if len(events) < page_size:
                    break
            else:
                log_func("error", {"message": "Failed to reach the monitoring endpoint. Retrying..."})
                break

        except Exception as e:
            log_func("error", {"message": f"Exception during monitoring: {str(e)}"})
            break

    if page == max_page - 1:
        log_func("info", {
            "message": "Maximum number of pages per response reached, "
                       "the elements on the next pages will not be read"
        })

    if all_events:
        helper.save_check_point(
            f'previous_query_date_iso_utc-{config_params["workspace_name"]}-{config_params["domain_url"]}',
            current_iso_date_utc
        )
