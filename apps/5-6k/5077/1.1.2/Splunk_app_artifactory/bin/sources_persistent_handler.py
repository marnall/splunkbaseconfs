import os
import sys
import json
import logging
import subprocess
import ast
import requests
from datetime import datetime

cur_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.abspath(os.path.join(cur_dir, 'libs'))
sys.path.append(cur_dir)
sys.path.append(lib_path)

import splunk.rest
from splunklib import client
import splunklib.client as client

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'artifactory.log'])
logging.basicConfig(filename=logfile,level=logging.DEBUG)

from splunk.persistconn.application import PersistentServerConnectionApplication

def flatten_query_params(params):
    # Query parameters are provided as a list of pairs and can be repeated, e.g.:
    #
    #   "query": [ ["arg1","val1"], ["arg2", "val2"], ["arg1", val2"] ]
    #
    # This function simply accepts only the first parameter and discards duplicates and is not intended to provide an
    # example of advanced argument handling.
    flattened = {}
    for i, j in params:
        flattened[i] = flattened.get(i) or j
    return flattened


class SourcesPersistentHandler(PersistentServerConnectionApplication):

    """
    """
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    """
    """
    def handle(self, in_string):
        request = json.loads(in_string)
        payload = {'success': False,'message': 'Dont run'}
        if request.get('method') == 'POST':
            params = request.get('form')
            body = {}
            for i in params:
                body[i[0]] = i[1]
            token = request.get('session')['authtoken']
            macros = client.Service(token=token,app='Splunk_app_artifactory', autologin=True).confs['macros']
            result, payload = self._validate_license(body,macros,payload)
            if result['success'] == True:
                payload = self._handle_post(body,macros,payload,result)
            else:
                payload['message'] = result['message']
        elif request.get('method') == 'GET':
            token = request.get('session')['authtoken']
            macros = client.Service(token=token,app='Splunk_app_artifactory', autologin=True).confs['macros']
            payload = self._handle_get(macros,payload)
        else:            
            payload['message'] = 'Request dont valid'
        if payload['success'] != True:
            self._remove_values(macros)
        return {'payload': payload}
        
    """
    """
    def _handle_post(self,body,macros,payload,result):
        try:
            for i in macros:
                if i.name == 'artifactory_sources':
                    i.update(**{'definition':'source="'+body['artifactory_source']+'" sourcetype="'+body['artifactory_source_type']+'" index="'+body['artifactory_index']+'"'})
                elif i.name == 'request_source':
                    i.update(**{'definition':'source="'+body['request_source']+'" sourcetype="'+body['request_source_type']+'" index="'+body['request_index']+'"'})
                elif i.name == 'artifactory_sources_macro':
                    i.update(**{'source':body['artifactory_source'],'source_type':body['artifactory_source_type'],'index':body['artifactory_index']})
                elif i.name == 'request_source_macro':
                    i.update(**{'source':body['request_source'],'source_type':body['request_source_type'],'index':body['request_index']})
                elif i.name == 'last_connection(5)':
                    i.update(**{'date':result['date'],'email':body['mail'],'key':body['key'],'company':body['company'],'contact_person':body['contact_person']})
                    payload['message'] = result['message']
                payload['success'] = True
        except Exception as e:
            logging.debug("UPDATE ERROR %s",e)
        return payload

    """
    """
    def _handle_get(self,macros,payload):
        try:
            for i in macros:
                if i.name == 'artifactory_sources_macro':
                    payload['artifactory_source'] = i.content['source'] 
                    payload['artifactory_source_type'] = i.content['source_type'] 
                    payload['artifactory_index'] = i.content['index'] 
                elif i.name == 'request_source_macro':
                    payload['request_source'] = i.content['source'] 
                    payload['request_source_type'] = i.content['source_type'] 
                    payload['request_index'] = i.content['index'] 
                elif i.name == 'last_connection(5)':
                    payload['key'] = i.content['key'] 
                    payload['mail'] = i.content['email'] 
                    payload['company'] = i.content['company'] 
                    payload['contact_person'] = i.content['contact_person'] 
                elif i.name == 'license':
                    payload['license'] = i.content['license']
        except Exception as e:
            payload = {'artifactory_source':'','artifactory_source_type':'','artifactory_index':'','request_source':'','request_source_type':'','request_index':'','key':'','mail':'','company':'','contact_person':''}
            payload['message'] = 'You dont have last values'
        payload['success'] = True
        return payload

    """
    """
    def _validate_license(self,body,macros,payload):
        try:
            logging.debug("BODY %s",body)
            values = {"application":'artifactory',"key":body["key"],"mail":body["mail"],"IP":body["IP"],"company":body["company"],"contact_person":body["contact_person"]}
            response = requests.post("http://167.71.186.103:3000/credentials",json=values)
            result = response.json()
        except:
            result = {}
            for i in macros:
                if i.name == 'last_connection(5)':
                    try:
                        result['date'] = i.content['date']
                        if(datetime.strptime(result['date'],'%Y-%m-%d') < datetime.now()):
                            result['success'] = False
                            result['message'] =  'Credential expired'
                            payload['message'] = 'Credential expired'
                        else:
                            result['success'] = True
                            result['message'] = 'Credentials expired '+datetime.strptime(result['date'],'%Y-%m-%d')
                            payload['message'] = 'Credentials expired '+datetime.strptime(result['date'],'%Y-%m-%d')
                    except:
                        result['success'] = False
                        result['message'] = 'Service down to create a key'
                        payload['message'] = 'Service down to create a key'
        if result['success'] == True:
            for i in macros:
                if i.name == 'license':
                    i.update(**{'license':1})
        return result, payload

    """
    """
    def _remove_values(self,macros):
        for i in macros:
            if i.name == 'request_source':
                i.update(**{'definition':'source="file1.log" sourcetype="file" index=""'})
            elif i.name == 'artifactory_sources':
                i.update(**{'definition':'source="file2.log" sourcetype="file" index=""'})
            elif i.name == 'license':
                i.update(**{'license':0})