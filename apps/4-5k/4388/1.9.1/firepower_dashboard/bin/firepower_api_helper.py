import os
import sys
import json
import requests
import time
import splunklib.client as client

splunk_home = os.getenv('SPLUNK_HOME')
sys.path.append(splunk_home + '/etc/apps/firepower_dashboard/bin/')
sys.path.append(splunk_home + '/etc/apps/firepower_dashboard/bin/apputils')

from logger import setup_logging as create_logger
from config_reader import ConfigReader
logger = create_logger('firepower_logger', 'firepower.log')

cached_config = {}
last_updated_time = time.time()
cache_expires_in = 300

class APIHelper (object):

    def invoke_api(self, endpoint_name,  param_value = None, data = None):

        global enpoints
        cached_config = self.getconfigdata()
        BASE_URL = cached_config['base_url']
        if BASE_URL.endswith('/'):
            BASE_URL = BASE_URL[:-1]
        API_URL = endpoint_name
        URL = BASE_URL+API_URL
        endpoint_response = None
        token = self.get_token()
        api_headers = {'content-type': 'application/json', 'Authorization': 'JWT {0}'.format(token)}

        start_time = time.time()
        endpoint_response = requests.get(URL,headers=api_headers,verify=False)
        end_time = time.time()
        time_taken =  end_time -start_time
        logger.info('Time taken to invoke api {0}: {1}'.format(API_URL,str((time_taken))))

        return json.loads(endpoint_response.content)


    def invoke_POST_api(self, endpoint_name, data = None):

        global enpoints
        result = None
        cached_config = self.getconfigdata()
        BASE_URL = cached_config['base_url']
        if BASE_URL.endswith('/'):
            BASE_URL = BASE_URL[:-1]
        API_URL = endpoint_name
        URL = BASE_URL+API_URL
        endpoint_response = None
        token = self.get_token()
        api_headers = {'content-type': 'application/json', 'Authorization': 'JWT {0}'.format(token)}
        try:
            endpoint_response = requests.post(URL,headers=api_headers,data=data,verify=False)
            result = endpoint_response.text
        except Exception as exp:
            logger.error('Error while invoking API:'+ URL)
            result = json.dumps({'msg':str(exp)})
            pass

        return json.loads(result)


    def invoke_PUT_api(self, endpoint_name, data = None):

        global enpoints
        result = None
        cached_config = self.getconfigdata()
        BASE_URL = cached_config['base_url']
        if BASE_URL.endswith('/'):
            BASE_URL = BASE_URL[:-1]
        API_URL = endpoint_name
        URL = BASE_URL+API_URL
        endpoint_response = None
        token = self.get_token()
        api_headers = {'content-type': 'application/json', 'Authorization': 'JWT {0}'.format(token)}
        try:
            endpoint_response = requests.put(URL,headers=api_headers,data=data,verify=False)
        except Exception as exp:
            logger.error('Error while invoking API:'+ URL)
            endpoint_response.content = {'msg':str(exp)}
            pass

        return json.loads(endpoint_response.content)


    def last_updated_time_dif(self):
        global last_updated_time
        return int(last_updated_time - time.time())


    def get_token(self):
        pswd = ''
        usname = ''
        global enpoints
        cached_config = self.getconfigdata()
        headers = {'content-type': 'application/json'}
        splunkServer = "localhost"
        splunkAdmin = "admin"
        splunkPassword = "changeme"
        splunkDestApp = "Endgame"
        if splunkDestApp:
            splunkService = client.connect(host=splunkServer, port=8089, username=splunkAdmin, password=splunkPassword, app=splunkDestApp)
        else:
            splunkService = client.connect(host=splunkServer, port=8089, username=splunkAdmin, password=splunkPassword)
        storage_passwords = splunkService.storage_passwords
				
        for credential in storage_passwords:
            pswd= credential.content.get('clear_password')
            usname= credential.content.get('username')
            break

        logger.info('pswd>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'+str(pswd))
        logger.info('usname>>>>>>>>>>>>>>>>>>>>>>>>>>>>'+str(usname))
        base_url = cached_config['base_url']
        if base_url.endswith('/'):
            base_url = base_url[:-1]
        LOGIN_URL = base_url + '/api/auth/login'
        payload = {"username": usname, "password": pswd}
        logger.info('payload>>>>>>>>>>>>>>>>>>.'+str(payload))
        response = requests.post(LOGIN_URL, headers=headers, data=json.dumps(payload), verify=False)
        auth_response = json.dumps(response.content)
        auth_response_json = json.loads(auth_response)
        token = json.loads(auth_response_json.encode('utf-8'))['metadata']['token']
        return token


    def getconfigdata(self):
        global cached_config
        global last_updated_time
        global cache_expires_in

        time_diff = int(self.last_updated_time_dif())
        if len(cached_config) < 1 or  time_diff > cache_expires_in:
            logger.info('Refreshing config settings')
            if time_diff > cache_expires_in:
                last_updated_time = time.time()
            configreader = ConfigReader()
            cached_config = configreader.readConfFile('appsetup.conf', 'app_config')
        return cached_config
    
    def getNativeAppBaseURL(self):
        cached_config = self.getconfigdata()
        BASE_URL = cached_config['native_base_url']
        if BASE_URL.endswith('/'):
            BASE_URL = BASE_URL[:-1]

        return {'url':BASE_URL}