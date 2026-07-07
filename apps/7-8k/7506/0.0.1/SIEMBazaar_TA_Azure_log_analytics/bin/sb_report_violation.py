import requests
import json
import sb_consts as sc


def report_violation(app_id, l_key):
    url = f"{sc.SB_DOMAIN}{sc.SB_REPORTVIOLATION_URL}"

    payload = json.dumps({
    "application": app_id,
    "license_key": l_key
    })
    headers = {
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response