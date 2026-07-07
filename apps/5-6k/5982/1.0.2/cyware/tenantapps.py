import base64
import hashlib
import hmac
import time
import requests
import urllib


class TenantAppsAuth:
    """
    An object which makes request on your behalf
    """

    def __init__(self, access_id, secret_key, server):
        self.access_id = access_id
        self.secret_key = secret_key
        self.server = "https://" + server + "/api/tenantapps/"

    def signature(self, expires):
        to_sign = '%s\n%i' % (self.access_id, expires)
        return base64.b64encode(
            hmac.new(
                self.secret_key.encode('utf-8'),
                to_sign.encode('utf-8'),
                hashlib.sha1).digest())

    def query(self, method, url, data=None, **params):
        expires = int(time.time() + 300)
        params['AccessID'] = self.access_id
        params['Expires'] = expires
        params['Signature'] = self.signature(expires)
        url = url + "?" + urllib.urlencode(params)
        if method == 'GET':
            resp = requests.get(url)
            status_code = resp.status_code
            try:
                json_data = resp.json()
                response = {
                    'data': json_data,
                    'status': status_code
                }
                return response
            except Exception as e:
                print(e)
                response = {
                    'data': resp.text,
                    'status': status_code
                }
                return response
        elif method == 'POST':
            headers = {'content-type': 'application/json'}
            resp = requests.post(url, json=data, headers=headers)
            status_code = resp.status_code
            try:
                json_data = resp.json()
                response = {
                    'data': json_data,
                    'status': status_code
                }
                return response
            except Exception as e:
                print(e)
                response = {
                    'data': resp.text,
                    'status': status_code
                }
                return response
        else:
            return None

    def report_incident(self, data, **params):
        cyb_token = "13f32e3e-e72a-406a-bb07-e74a23f82187"
        url = self.server + "report_incident/"
        return self.query("POST", url, data,cyb_token=cyb_token, **params)

    def list_incident_reported(self, **params):
         cyb_token = "d7769ea6-70ff-479e-99d7-85b2e0d4a4e9"
         url = self.server + "list_incident_reported/"
         return self.query("GET", url, cyb_token=cyb_token, **params)

    def create_card(self, data, **params):
         cyb_token = "64ec6149-4371-4101-b5be-680c43c3995e"
         url = self.server + "create_card/"
         return self.query("POST", url, data, cyb_token=cyb_token, **params)

    def test_connectivity(self, **params):
         cyb_token = "74268378-a202-4778-b611-6e50c787b694"
         url = self.server + "test_connectivity/"
         return self.query("GET", url, cyb_token=cyb_token, **params)
