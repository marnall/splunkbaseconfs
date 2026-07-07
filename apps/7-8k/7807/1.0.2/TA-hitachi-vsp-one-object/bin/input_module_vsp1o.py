#!/usr/bin/env python3
import requests
import json
import logging
from urllib.parse import urlparse

def mask_sensitive_data(text, mask_char='*'):
    """Mask sensitive data in logs."""
    return mask_char * 8 if text else ''

def collect_events(helper, ew):
    """
    Retrieves an access token from the token endpoint, then uses the CSRF token URL
    to obtain the CSRF token and session cookies. Finally, it queries the Prometheus API.
    """

    # Set up Splunk logging
    logger = logging.getLogger('splunk')
    logger.setLevel(logging.INFO)

    # Retrieve global settings and input parameters
    REGION = helper.get_global_setting("prometheus_region").strip()
    CLUSTER_NAME = helper.get_global_setting("prometheus_cluster_name").strip()
    helper.log_info("CLUSTER_NAME: " + CLUSTER_NAME)
    CLIENT_ID = helper.get_global_setting("client_id").strip()
    helper.log_info("CLIENT_ID: " + CLIENT_ID)
    CLIENT_SECRET = helper.get_global_setting("client_secret").strip()
    helper.log_info("CLIENT_SECRET: [REDACTED]")
    PROM_QUERY = helper.get_arg("prometheus_query").strip()
    helper.log_info("PROM_QUERY: " + PROM_QUERY)

    # Validate required values
    if not (REGION and CLUSTER_NAME and CLIENT_ID and CLIENT_SECRET and PROM_QUERY):
        raise Exception("One or more required global settings or input parameters are missing.")

    # Construct token endpoint using the GMS domain.
    token_endpoint = f"https://admin.gms.{CLUSTER_NAME}/ui/auth/realms/vsp-object/protocol/openid-connect/token"
    logger.info("token endpoint: " + token_endpoint)
    helper.log_info("Constructed token endpoint: " + token_endpoint)

    # Construct CSRF token URL
    csrf_token_url_template = helper.get_global_setting("csrf_token_generation_url").strip()
    helper.log_info("csrf_token_url_template: " + csrf_token_url_template)
    csrf_token_url = csrf_token_url_template.replace("{{prometheus_region}}", REGION).replace("{{cluster_name}}", CLUSTER_NAME)
    helper.log_info("Constructed CSRF token URL: " + csrf_token_url)

    # HTTPS Scheme Validation for CSRF URL (Line ~90 Fix)
    if urlparse(csrf_token_url).scheme.lower() != 'https':
        helper.log_error("Invalid csrf_token_generation_url: HTTPS scheme is required.")
        raise ValueError("csrf_token_generation_url must use HTTPS")

    # Construct Prometheus query endpoint
    prometheus_base_url_template = helper.get_global_setting("prometheus_base_url").strip()
    prometheus_base_url = (prometheus_base_url_template
                          .replace("{{prometheus_region}}", REGION)
                          .replace("{{cluster_name}}", CLUSTER_NAME))
    prom_endpoint = f"{prometheus_base_url}{PROM_QUERY}"
    helper.log_info("Constructed Prometheus endpoint: " + prom_endpoint)

    # HTTPS Scheme Validation for Prometheus URL (Line ~113 Fix)
    if urlparse(prometheus_base_url).scheme.lower() != 'https':
        helper.log_error("Invalid prometheus_base_url: HTTPS scheme is required.")
        raise ValueError("prometheus_base_url must use HTTPS")

    #############################################
    # 1. Get the Access (Bearer) Token
    #############################################
    token_payload = (
        "grant_type=client_credentials"
        "&client_id=" + CLIENT_ID +
        "&client_secret=" + mask_sensitive_data(CLIENT_SECRET)
    )
    helper.log_info("Payload: " + token_payload)

    token_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    helper.log_info("Requesting access token from token endpoint...")
    token_response = requests.post(token_endpoint, data=token_payload.replace(mask_sensitive_data(CLIENT_SECRET), CLIENT_SECRET), headers=token_headers, verify=True)
    helper.log_info("Token response status code: " + str(token_response.status_code))

    if token_response.status_code != 200:
        raise Exception("Failed to get token: " + token_response.text)

    token_json = token_response.json()
    access_token = token_json.get("access_token")

    if not access_token:
        raise Exception("Access token not found in token response.")
    helper.log_info("Access token obtained: " + mask_sensitive_data(access_token))

    #############################################
    # 2. Get the CSRF Token and Session Cookies
    #############################################
    session_obj = requests.Session()  # Create a session to persist cookies
    helper.log_info("Retrieving CSRF token and session cookies from: " + csrf_token_url)

    csrf_response = session_obj.get(csrf_token_url, verify=True)

    if csrf_response.status_code != 200:
        helper.log_error("Failed to get CSRF token: " + csrf_response.text)
        raise Exception("Failed to get CSRF token: " + csrf_response.text)

    xsrf_token = session_obj.cookies.get("XSRF-TOKEN")
    vertx_session = session_obj.cookies.get("vertx-web.session")
    helper.log_info("XSRF Token: " + mask_sensitive_data(xsrf_token))
    helper.log_info("Vertx Session: " + mask_sensitive_data(vertx_session))

    #############################################
    # 3. Query the Prometheus Endpoint
    #############################################
    query_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    if xsrf_token:
        query_headers["X-XSRF-TOKEN"] = xsrf_token

    helper.log_info("Querying Prometheus API at: " + prom_endpoint)
    prom_response = session_obj.get(prom_endpoint, headers=query_headers, verify=True, allow_redirects=True)
    helper.log_info("Response Status: " + str(prom_response.status_code))

    content_type = prom_response.headers.get("Content-Type", "").lower()
    helper.log_info("Content Type: " + content_type)

    if "application/json" not in content_type:
        helper.log_error("Received non-JSON response. Response body: [REDACTED]")
        raise Exception("Received non-JSON response, expected JSON. Check if the endpoint supports API access with your token.")

    try:
        prom_data = prom_response.json()
        helper.log_info("Prometheus API returned JSON: [REDACTED]")

        event = helper.new_event(
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=helper.get_sourcetype(),
            data=json.dumps(prom_data)
        )
        helper.log_info("Index: " + helper.get_output_index())
        helper.log_info("Source Type: " + helper.get_sourcetype())

        ew.write_event(event)
        helper.log_info("Successfully ingested Prometheus data into Splunk. Query: " + PROM_QUERY)

    except json.JSONDecodeError as e:
        helper.log_error("Error decoding JSON: " + str(e))
        helper.log_error("Raw response: [REDACTED]")
        raise

if __name__ == '__main__':
    print("This script is intended to be run as a Splunk modular input.")