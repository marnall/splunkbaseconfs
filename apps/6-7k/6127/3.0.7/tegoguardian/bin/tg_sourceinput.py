import sys
import os
import requests as req
import json
import splunk.entity
import splunklib.client as client


def tg_api_call(license, amounttofetch, parameters):
    response = req.get(
        url="https://ti.tegocyber.com/api/Main/get/" + amounttofetch, params=parameters, headers={"license": license})
    if response.status_code != 200:
        print(response.json())
        exit()
    data = response.json()
    return json.dumps(data)


def main():
    sessionKey = sys.stdin.readline().strip()
    app_name = "tegoguardian"
    entity = splunk.entity.getEntity(
        "/configs/conf-app", "install", namespace="tegoguardian", sessionKey=sessionKey, owner="nobody")
    amounttofetch = entity.get("amounttofetch")

    service = client.connect(app=app_name, token=sessionKey)
    storage_passwords = service.storage_passwords
    for storage_password in storage_passwords.list():
        if storage_password.name == "tegoguardian_license:admin:":
            license = storage_password.clear_password
    threats = tg_api_call(license, amounttofetch, {})
    data = json.loads(threats)
    print(json.dumps(data))


main()
