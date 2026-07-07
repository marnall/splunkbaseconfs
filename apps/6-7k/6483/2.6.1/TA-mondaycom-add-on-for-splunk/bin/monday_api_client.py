from configparser import RawConfigParser
import os
import json
import requests


VERSION = "2.6.0"
USER_AGENT = f'Splunk-monday-addon/{VERSION}'
EVENTS_PER_PAGE = 500

MONDAY_API_VERSION = "2025-07"
MONDAY_API_URL = 'https://api.monday.com/v2'
DEV_MONDAY_API_URL = 'http://monday.llama.fan/v2'

in_dev_mode = False #True if os.environ.get('MONDAY_DEV') else False
verify_ssl = not in_dev_mode
monday_api_url = DEV_MONDAY_API_URL if in_dev_mode else MONDAY_API_URL

class MondayApiClient:
    def __init__(self, helper, api_token):
        self._helper = helper
        self._api_token = api_token

    @staticmethod
    def check_api_token(api_token, helper):
        try:
            headers = { "Authorization": f"Bearer {api_token}", "User-Agent": USER_AGENT, "Accept": "application/json", "Content-Type": "application/json", "API-Version": MONDAY_API_VERSION}
            payload = { "query": "query { audit_logs(page: 1, limit: 1) { logs { timestamp } } }" }
            response = helper.send_http_request(monday_api_url, "POST", parameters=None, payload=payload,
                                                headers=headers, cookies=None, cert=None,
                                                timeout=None, use_proxy=False, verify=verify_ssl)


            response.raise_for_status()
            
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 401:
                raise ValueError(f"Invalid API token. Please check your API token and try again.")
            raise ValueError(f"Something went wrong with the Monday.com API, please try again later. Error: {error}")

    def fetch_audit_logs(self, request_data):
        query = """
        query getAuditLogs($start_time: ISO8601DateTime, $end_time: ISO8601DateTime, $limit: Int!, $page: Int!) {
            audit_logs(start_time: $start_time, end_time: $end_time, limit: $limit, page: $page) {
                logs {
                    timestamp
                    account_id
                    user {
                        id
                        name
                        email
                    }
                    event
                    slug
                    ip_address
                    user_agent
                    client_name
                    client_version
                    os_name
                    os_version
                    device_name
                    device_type
                    activity_metadata
                }
                pagination {
                    has_more_pages
                    next_page_number
                }
            }
        }
        """

        variables = {
            "start_time": request_data["start_date"],
            "end_time": request_data["end_date"],
            "limit": EVENTS_PER_PAGE,
            "page": request_data["page"]
        }

        payload = {
            "query": query,
            "variables": variables
        }

        headers = {'Authorization': 'Bearer {}'.format(self._api_token), 'User-Agent': USER_AGENT, "Accept": "application/json", "Content-Type": "application/json", "API-Version": MONDAY_API_VERSION}
        response = self._helper.send_http_request(monday_api_url, "POST", parameters=None, payload=payload,
                                                  headers=headers, cookies=None, cert=None,
                                                  timeout=None, use_proxy=False, verify=verify_ssl)

        response.raise_for_status()

        result = response.json()["data"]["audit_logs"]
        logs = result["logs"]

        for log in logs:
            log["user_id"] = log["user"]["id"]
            log["user_email"] = log["user"]["email"]
            log["user_name"] = log["user"]["name"]
            del log["user"]

        return {
            'logs': logs,
            'next_page': result["pagination"]["next_page_number"]
        }

