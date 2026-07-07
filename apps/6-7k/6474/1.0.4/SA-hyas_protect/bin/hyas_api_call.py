from requests import get
from json import dumps


class Hyas_api_call:

    def hyas_protect_endpoints(url, api_key):
        try:

            headers = {
                "Content-type": "application/json",
                "X-API-Key": api_key,
                'User-Agent': 'Splunk Enterprise'
            }
            hyas_data = get(url, headers=headers)
            if hyas_data.status_code == 401:
                data = 401
                return data
            elif hyas_data.status_code >= 500:
                data = 500
                return data
            else:
                data = hyas_data.json()
                return data

        except Exception as err:
            return err

    def api_key_call(storage_passwords):
        for credential in storage_passwords:
            realm = credential.content.get("realm")
            if realm == "hyas_realm":
                usercreds = {"password": credential.content.get("clear_password")}
                return usercreds["password"]
