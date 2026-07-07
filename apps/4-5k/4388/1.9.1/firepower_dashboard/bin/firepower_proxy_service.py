# System import
import splunk
import os
import sys
import json


splunk_home = os.getenv('SPLUNK_HOME')
sys.path.append(splunk_home + '/etc/apps/firepower_dashboard/bin/')
sys.path.append(splunk_home + '/etc/apps/firepower_dashboard/bin/apputils')

from logger import setup_logging as create_logger
logger = create_logger('firepower_logger', 'firepower.log')

from firepower_api_helper import APIHelper
from splunk.persistconn.application import PersistentServerConnectionApplication


# Append PYTHONPATH so script will load corresponding library
LOG_MAX_SIZE_BYTES = 1024 ** 2 * 100
LOG_MAX_ROTATIONS = 5

enpoints={
    'setup':'/api/v1/setup'
}

class RESTHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, payload):

        global logger
        logger.info('Received request...')
        response = {}
        result = {}
        try:
            # get the http method
            json_data = json.loads(payload)
            method = json_data['method']
            logger.info('Verb used is {0}'.format(method))
        except:
            raise Exception('handle: %s' % (sys.exc_info()[0]))

        if method == 'GET':
            result = self.handleGET(json_data)

        elif method == 'POST':
            result = self.handlePOST(json_data)

        elif method == 'PUT':
            result = self.handlePUT(json_data)

        elif method == 'DELETE':
            result = self.handleDELETE(json_data)

        else:
            logger.info('Unknown/unsupported verb')
            pass

        response['payload'] = result
        logger.info('Send response...')
        return response


    def handleGET(self,data):
        global logger
        logger.info('Method GET called:'+str(data))

        return "result"


    def handlePOST(self,data):
        global logger

        logger.info('Method POST called:'+str(data))
        logger.info('Payload:'+data['payload'])
        
        return "result"


    def handlePUT(self,data):
        global logger
        result = {}
        apihelper = APIHelper()
        logger.info('Method PUT called:' + str(data))
        data = json.loads(json.dumps(data))
        
        try:
            url = enpoints[data['rest_path'].replace('/firepower_dashboard/put/','')]
        except Exception as exp:
            logger.error('Error while getting url'+str(exp))
            result['payload'] = {'msg':str(exp)}

        try:
            result['payload'] = apihelper.invoke_PUT_api(url,data['payload'])
        except Exception as exp:
            logger.error('Error while invoking invoke_PUT_api:'+ url)
            result['payload'] = {'msg':str(exp)}
            
        return result



    def handleDELETE(self,data):
        global logger
        logger.info('Method DELETE called')
        logger.info(json.dumps(data))
        return data

    def extract_apiname(self,params):
        api_name = None
        for param in params:
            if param[0] in 'source_api':
                api_name = str(param[1])
        return api_name

    def generateURL(self,params):
        urlstring = '?'
        for param in params:
            if param[0] not in 'source_api' and param[0] not in 'url_value' :
                urlstring = urlstring+str(param[0]+'='+str(param[1])+'&')
            elif param[0] in 'url_value':
                urlstring = str(param[1])+'&'
                break

        return urlstring[:-1]
