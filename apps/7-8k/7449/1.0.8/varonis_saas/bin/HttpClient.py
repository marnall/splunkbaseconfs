import urllib3
import json
import os
import ssl

if not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
    ssl._create_default_https_context = ssl._create_unverified_context


def create_ssl_context():
    ctx = ssl._create_unverified_context()
    ctx.load_default_certs()
    ctx.options |= 0x4  # ssl.OP_LEGACY_SERVER_CONNECT
    return ctx


class HttpClient:

    def __init__(self, url, api_key):
        self.url = url.rstrip('\\').rstrip('\/')
        self.api_key = api_key
        self.authToken = None
        self.ctx = create_ssl_context()

    def execute_search_query(self, search_query, max_fetch=1000, last_fetched_ingest_time=None):
        if not self.authToken:
            self.get_auth_token()

        headers = {'Authorization': 'bearer ' + self.authToken, 'Content-type': 'application/json',
                   'varonis-integration': 'Splunk SIEM'}
        with urllib3.PoolManager(ssl_context=self.ctx) as http:
            fields = json.dumps(json.loads(search_query)).encode('utf-8')
            create_search = http.request("POST", self.url + '/api/search/v2/search', body=fields,
                                         headers=headers)
            try:
                create_search_data = json.loads(create_search.data)
                url = create_search_data[0]["location"]
                url_suffix = f'/api/search/{url}'
                if max_fetch:
                    url_suffix += f'?from=0&to={max_fetch - 1}'
            except Exception as e:
                try:
                    response_content = f"Content:" + create_search.data.decode('utf-8')
                except Exception as e:
                    response_content = create_search.data
                raise Exception(f'[HttpClient] Exception in execute_search_query. {e} Status code: {str(create_search.status)} {response_content}')

            while True:
                data_response = http.request('GET', self.url + url_suffix, headers=headers)
                if data_response.status in [301, 302, 304, 405, 206]:
                    continue
                if data_response.status == 200:
                    json_data = json.loads(data_response.data)
                    return json_data
                raise Exception(f'Request error status: {data_response.status}')



    def get_enum(self, enum_id):
        if not self.authToken:
            self.get_auth_token()

        headers = {'Authorization': 'bearer ' + self.authToken, 'Content-type': 'application/json',
                   'varonis-integration': 'Splunk SIEM'}
        with urllib3.PoolManager(ssl_context=self.ctx) as http:
            response = http.request("GET", self.url + f'/api/entitymodel/enum/{enum_id}', headers=headers)
            if response.status == 200:
                response_data = json.loads(response.data)
                return response_data
            else:
                raise Exception(f'get_enum {enum_id} failed: ' + response.status)

    def add_note_to_alerts(self, query):
        if not self.authToken:
            self.get_auth_token()

        headers = {'Authorization': 'bearer ' + self.authToken, 'Content-type': 'application/json',
                   'varonis-integration': 'Splunk SIEM'}
        with urllib3.PoolManager(ssl_context=self.ctx) as http:
            fields = json.dumps(query).encode('utf-8')
            response = http.request("POST", self.url + '/api/alert/alert/AddNoteToAlerts', body=fields, headers=headers)
            if response.status == 200:
                return True
            else:
                raise Exception('add_note_to_alerts failed: ' + response.status)

    def alert_update_status(self, query):
        if not self.authToken:
            self.get_auth_token()

        headers = {'Authorization': 'bearer ' + self.authToken, 'Content-type': 'application/json',
                   'varonis-integration': 'Splunk SIEM'}
        with urllib3.PoolManager(ssl_context=self.ctx) as http:
            fields = json.dumps(query).encode('utf-8')
            response = http.request("POST", self.url + '/api/alert/alert/SetStatusToAlerts', body=fields,
                                    headers=headers)
            if response.status == 200:
                return True
            else:
                response_content = None
                try:
                    response_content = f"Content:" + response.data.decode('utf-8')
                except Exception as e:
                    response_content = ''
                raise Exception(f'[HttpClient] alert_update_status failed. Status code: {str(response.status)} {response_content}')

    def get_auth_token(self):
        data = {'grant_type': 'varonis_custom'}
        headers = {'x-api-key': self.api_key,
                   'Content-Type': 'application/x-www-form-urlencoded',
                   'varonis-integration': 'Splunk SIEM'}

        with urllib3.PoolManager(ssl_context=self.ctx) as http:
            response = http.request("POST", self.url + '/api/authentication/api_keys/token', encode_multipart=False,
                                    fields=data, headers=headers)
            if response.status == 200:
                try:
                    response_data = json.loads(response.data)
                except ValueError as e:
                    raise Exception(f'InvalidURL')

                response_data = json.loads(response.data)
                self.authToken = response_data['access_token']
                return True
            else:
                raise Exception(f'Auth Failed: response.status = {response.status}, response.data = {response.data.decode("utf-8")}')
