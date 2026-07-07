import requests
import json
import logging

class InputCCM():
    def __init__(self,client_secret_id, job_id, BASE_URL, proxy_server, app_name, app_version):
        self.client_secret_id = client_secret_id
        self.job_id = job_id
        self.BASE_URL = BASE_URL
        self.proxy_server = proxy_server
        self.app_name = app_name
        self.app_version = app_version

    def get_data_from_ccm(self):
        headers = {
            'client_secret_id': self.client_secret_id,
            'User-Agent': f'{self.app_name}/{self.app_version}'
        }
        url = f'{self.BASE_URL}/v1/ccm/jobs/{self.job_id}/get-content'
        if not url.startswith("https"):
            logging.critical("URL must be HTTPS")
            exit(1)
        try:
            response = requests.get(url=url, headers=headers, proxies=self.proxy_server, verify=True)
        except Exception as err:
            logging.error(f'Error while getting data from job "{self.job_id}". Error message: {err}')
            return None
        if response.ok:
            data = response.json()
            logging.info(f'Obtained rules from "{self.job_id}" job. Number of rules: {len(data)}')
            return data
        else:
            logging.error(f'Error while getting data from job id "{self.job_id}". Response status code: {response.status_code}. Error message: {response.text}')
            return None

    def post_ccm_stat(self, body):
        URL_PREFIX = "/v1/mark-rules-as-deployed"
        url = f'{self.BASE_URL}{URL_PREFIX}/'
        if not url.startswith("https"):
            logging.critical("URL must be HTTPS")
            exit(1)
        headers = {
            'client_secret_id': self.client_secret_id,
            'User-Agent': f'{self.app_name}/{self.app_version}'
        }
        try:
            response = requests.post(url=url, headers=headers, data=body, proxies=self.proxy_server)
        except Exception as err:
            message = f'Error while post stat data to the TDM. Error message: {err}. Message: {body}.'
            logging.error(message)
        if response.ok:
            logging.info(f'Successfully uploaded stat data to the TDM. Message: {body}.')
        else:
            message = f'Error while posting stat data to the TDM. Response status code: {response.status_code}. Error message: {response.text}. Message: {body}.'
            logging.error(message)


    def gen_chunks_to_object(self, data, chunksize=50):
        chunk = []
        for index, line in enumerate(data):
            if (index % chunksize == 0 and index > 0):
                yield chunk
                del chunk[:]
            chunk.append(line)
        yield chunk

    def post_ccm_stat_gen_chunks(self, data):
        for chunk in self.gen_chunks_to_object(data, chunksize=50):
            obj_array = []
            for row in chunk:
                if row != None and row != '':
                    obj_array.append(row)
            body = json.dumps(obj_array)
            self.post_ccm_stat(body)