# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests

# For advanced users, if you want to create single instance mod input, uncomment this method.
# def use_single_instance_mode():
#     return True


def validate_input(helper, definition):
    """Validate input stanza configurations."""
    client_id = definition.parameters.get('client_id')
    client_secret = definition.parameters.get('client_secret')
    authorization_code = definition.parameters.get('authorization_code')
    site24x7_account_domain = definition.parameters.get('site24x7_account_domain')

    if not all([client_id, client_secret, site24x7_account_domain]):
        raise ValueError("Missing required OAuth configuration values: client_id, client_secret, or site24x7_account_domain.")
    
    if not authorization_code and not helper.get_check_point(f"site24x7_refresh_token_{client_id}_{site24x7_account_domain}"):
        raise ValueError("Authorization code is required for initial setup if no refresh token exists.")


def generate_refresh_token(helper, client_id, client_secret, authorization_code, site24x7_account_domain):
    """Generate the refresh token using authorization code (One-Time Step)."""
    zoho_domain = site24x7_account_domain.replace("site24x7.", "accounts.zoho.")
    token_url = f"https://{zoho_domain}/oauth/v2/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": authorization_code,
        "grant_type": "authorization_code"
    }
    response = requests.post(token_url, data=payload)

    if response.status_code == 200:
        refresh_token = response.json().get("refresh_token")
        if refresh_token:
            helper.log_info(f"Successfully obtained refresh token: {refresh_token}")
            return refresh_token
        else:
            helper.log_error("No refresh token returned. Ensure the authorization code is valid.")
    else:
        helper.log_error(f"Failed to generate refresh token: {response.text}")
        raise ValueError("Refresh token generation failed")


def get_access_token(helper, client_id, client_secret, refresh_token, site24x7_account_domain):
    """Generate a new access token using the refresh token."""
    zoho_domain = site24x7_account_domain.replace("site24x7.", "accounts.zoho.")
    token_url = f"https://{zoho_domain}/oauth/v2/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    response = requests.post(token_url, data=payload)

    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        helper.log_error(f"Failed to refresh access token: {response.text}")
        raise ValueError("Token refresh failed")


def collect_events(helper, ew):
    """Collect events from Site24x7 and send them to Splunk with checkpointing."""
    input_name = helper.get_input_stanza_names()[0]
    client_id = helper.get_arg('client_id')
    client_secret = helper.get_arg('client_secret')
    authorization_code = helper.get_arg('authorization_code')
    site24x7_account_domain = helper.get_arg('site24x7_account_domain')

    checkpoint_key = f"site24x7_refresh_token_{client_id}_{input_name}_{site24x7_account_domain}"

    try:
        # Attempt to retrieve the refresh token from checkpoint
        refresh_token = helper.get_check_point(checkpoint_key)

        if not refresh_token:
            # Generate and store refresh token if not found
            refresh_token = generate_refresh_token(helper, client_id, client_secret, authorization_code, site24x7_account_domain)
            helper.save_check_point(checkpoint_key, refresh_token)

        # Generate access token
        access_token = get_access_token(helper, client_id, client_secret, refresh_token, site24x7_account_domain)

        # Fetch Site24x7 monitors
        api_url = f"https://www.{site24x7_account_domain}/api/current_status?group_required=false&apm_required=true&suspended_required=true&locations_required=false&exclude_kube_workload=true"
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
        response = requests.get(api_url, headers=headers)

        # Log the entire JSON response
        helper.log_info(f"Full API Response: {response.text}")

        if response.status_code == 200:
            monitors = response.json().get("data", {}).get("monitors", [])
            for monitor in monitors:
                event_data = json.dumps(monitor)
                event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=event_data)
                ew.write_event(event)
            helper.log_info(f"Successfully processed {len(monitors)} monitors.")
        else:
            helper.log_error(f"Failed to fetch monitor data: {response.text}")

    except Exception as e:
        helper.log_error(f"Error in collect_events: {str(e)}")