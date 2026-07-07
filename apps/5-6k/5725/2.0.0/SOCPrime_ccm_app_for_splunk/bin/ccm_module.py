import logging
import requests
import sys,os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
import splunklib.client as client

proxies = {}
class InputCCM():
    def __init__(self,client_secret_id, job_id, BASE_URL, proxy_server):
        self.client_secret_id = client_secret_id
        self.job_id = job_id
        self.BASE_URL = BASE_URL
        self.proxy_server = proxy_server

    def get_data_from_ccm(self):
        headers = {
            'client_secret_id': self.client_secret_id
        }
        try:
            response = requests.get(url=f'{self.BASE_URL}ccm/jobs/{self.job_id}/get-content', headers=headers, proxies=self.proxy_server)
        except Exception as err:
            message = f'Error while getting data from job "{self.job_id}". Error message: {err}'
            raise Exception(message)

        if response.ok:
            data = response.json()
            logging.info(f'Obtained rules from "{self.job_id}" job. Number of rules: {len(data)}')
            return data
        else:
            message = f'Error while getting data from job id "{self.job_id}". Response status code: {response.status_code}. Error message: {response.text}'
            raise Exception(message)

    def post_ccm_stat(self, body):
        URL_PREFIX = "mark-rules-as-deployed"
        headers = {
            'client_secret_id': self.client_secret_id,
        }
        try:
            response = requests.post(url=f'{self.BASE_URL}{URL_PREFIX}/', headers=headers, data=body, proxies=self.proxy_server)
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