import os
import sys
import time
import json
import datetime
import requests

API_VERSION = "2023-06-01"

# get access token
def get_access_token(data, ms_url):
    with requests.post(ms_url, data=data) as r:
        r.raise_for_status()
        token_info = r.json()
        access_token = token_info.get('access_token')
    return access_token

def get_api_data(token, request_url):
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    with requests.get(request_url, headers=headers) as r:
        r.raise_for_status()
        return r.content.decode('utf-8')