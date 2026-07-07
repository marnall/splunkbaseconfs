from datetime import datetime
import requests

def get_host_url():
    """
    The function `get_host_url` returns the URL of the Host".
    """
    return "https://apis.syscloud.com/"

def get_authtoken(helper, headers):
    """
    The function `get_authtoken` retrieves an authentication token using client credentials.
    """

    clientid = helper.get_global_setting('clientid')
    secretid = helper.get_global_setting('secretid')

    url = get_host_url() + "auth/token"
    payload = f'client_id={clientid}&client_secret={secretid}'
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
        return 'bearer ' + response.json()['access_token']
    except requests.exceptions.RequestException as e:
        helper.log_error("Invalid Client Credentials " + e.strerror)
        exit()
