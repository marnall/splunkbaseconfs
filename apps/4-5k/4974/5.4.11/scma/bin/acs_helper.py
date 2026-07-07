import requests
import logging
import os
import json
import sys
import logging.handlers

from splunk.persistconn.application import PersistentServerConnectionApplication
import signal
import subprocess

import base64

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

splunk_home = os.environ['SPLUNK_HOME']
LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "scma.log"

def setup_logger():  # setup logging
    global SPLUNK_HOME, LOG_LEVEL, LOG_FILE_NAME
    if 'SPLUNK_HOME' in os.environ:
        SPLUNK_HOME = os.environ['SPLUNK_HOME']

    log_format = "%(asctime)s %(levelname)-s\t%(module)s[%(process)d]:%(lineno)d - %(message)s"
    logger = logging.getLogger('v')
    logger.setLevel(LOG_LEVEL)

    l = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk', LOG_FILE_NAME), mode='a', maxBytes=1000000, backupCount=2)
    l.setFormatter(logging.Formatter(log_format))
    logger.addHandler(l)

    # ..and (optionally) output to console
    logH = logging.StreamHandler()
    logH.setFormatter(logging.Formatter(fmt=log_format))
    # logger.addHandler(logH)

    logger.propagate = False
    return logger

logger = setup_logger()

def list_subnets(features,acs_url,stackname,headers):
    returnVal = { "IPAllowList" : [] }
    for feat in features :
        response = requests.get(acs_url+stackname+'/adminconfig/v2/access/'+feat+'/ipallowlists', headers=headers, verify=False)  # nosemgrep
        if response.status_code == 200 :
            resp = json.loads(response.text)
            resp["feature"] = feat
            returnVal["IPAllowList"].append(resp)

    return {'payload': returnVal, 'status': 200}

def list_outbounds(acs_url,stackname,headers):
    returnVal = {}

    response = requests.get(acs_url+stackname+'/adminconfig/v2/access/outbound-ports', headers=headers, verify=False)  # nosemgrep
    if response.status_code == 200 :
        resp = json.loads(response.text)
        returnVal["Outbounds"] = resp

    return {'payload': returnVal, 'status': 200}

def list_tokens(acs_url,stackname,headers):
    returnVal = {}

    response = requests.get(acs_url+stackname+'/adminconfig/v2/tokens', headers=headers, verify=False)  # nosemgrep
    if response.status_code == 200 :
        resp = json.loads(response.text)
        returnVal["Tokens"] = resp

    return {'payload': returnVal, 'status': 200}

def list_indexes(acs_url,stackname,headers):
    returnVal = {}

    response = requests.get(acs_url+stackname+'/adminconfig/v2/indexes', headers=headers, verify=False)  # nosemgrep
    if response.status_code == 200 :
        resp = json.loads(response.text)
        returnVal["Indexes"] = resp

    return {'payload': returnVal, 'status': 200}

def list_maintenances(acs_url,stackname,headers):
    returnVal = {}

    response = requests.get(acs_url+stackname+'/adminconfig/v2/maintenance-windows/schedules', headers=headers, verify=False)  # nosemgrep
    if response.status_code == 200 :
        resp = json.loads(response.text)
        returnVal["Maintenance_Windows"] = resp

    return {'payload': returnVal, 'status': 200}

def list_apps(acs_url,stackname,headers,experience):
    returnVal = {}
    apps_url = acs_url+stackname+"/adminconfig/v2/apps"
    if experience in ["victoria"] :
        apps_url = apps_url+"/victoria"

    response = requests.get(apps_url, headers=headers, verify=False)  # nosemgrep
    if response.status_code == 200 :
        resp = json.loads(response.text)
        returnVal["Private"] = resp
    
    if experience in ["victoria"] :
        apps_url = apps_url + "?splunkbase=true"
        response = requests.get(apps_url, headers=headers, verify=False)  # nosemgrep
        if response.status_code == 200 :
            resp = json.loads(response.text)
            returnVal["SplunkBase"] = resp

    return {'payload': returnVal, 'status': 200}

class ACS_Helper(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """

        #dbg.set_breakpoint()

        acs_url = "https://admin.splunk.com/"
        rest_url = ".splunkcloud.com:8089/"

        # Parse the arguments
        args = self.parse_in_string(in_string)
        
        token = ""
        if "token" in args['form_parameters'] :
            token = args['form_parameters']['token']
        
        stackname = ""
        if "stackname" in args['form_parameters'] :
            stackname = args['form_parameters']['stackname']
            if "stg-" in stackname :
                acs_url = "https://staging.admin.splunk.com/"
                rest_url = ".stg.splunkcloud.com:8089/"
        
        capability = ""
        if "capability" in args['form_parameters'] :
            capability = args['form_parameters']['capability']

        feature = ""
        if "feature" in args['form_parameters'] :
            feature = args['form_parameters']['feature']

        action = "list"
        if "action" in args['form_parameters'] :
            action = args['form_parameters']['action']
        
        token_user = ""
        token_audience = ""
        token_expire = ""
        token_id = ""
        subnets = ""
        port = ""
        token_username = ""
        token_password = ""

        index_name = ""
        index_datatype = ""
        index_maxdatasize = ""
        index_searchabledays = ""
        index_retention = ""
        index_storage = ""


        experience = "victoria"
        app_name = ""

        if "experience" in args['form_parameters'] :
            experience = args['form_parameters']['experience']
        
        if action in ["add","delete"] :
            if "subnets" in args['form_parameters'] :
                subnets = args['form_parameters']['subnets']
            
            if "port" in args['form_parameters'] :
                port = args['form_parameters']['port']
            
            if "token_user" in args['form_parameters'] :
                token_user = args['form_parameters']['token_user']

            if "token_audience" in args['form_parameters'] :
                token_audience = args['form_parameters']['token_audience']

            if "token_expire" in args['form_parameters'] :
                token_expire = args['form_parameters']['token_expire']
            
            if "token_id" in args['form_parameters'] :
                token_id = args['form_parameters']['token_id']
            
            if "token_username" in args['form_parameters'] :
                token_username = args['form_parameters']['token_username']
            
            if "token_password" in args['form_parameters'] :
                token_password = args['form_parameters']['token_password']
            
            if "index_name" in args['form_parameters'] :
                index_name = args['form_parameters']['index_name']

            if "index_datatype" in args['form_parameters'] :
                index_datatype = args['form_parameters']['index_datatype']
            
            if "index_maxdatasize" in args['form_parameters'] :
                index_maxdatasize = args['form_parameters']['index_maxdatasize']
            
            if "index_searchabledays" in args['form_parameters'] :
                index_searchabledays = args['form_parameters']['index_searchabledays']
            
            if "index_retention" in args['form_parameters'] :
                index_retention = args['form_parameters']['index_retention']
            
            if "index_storage" in args['form_parameters'] :
                index_storage = args['form_parameters']['index_storage']
            
            if "app_name" in args['form_parameters'] :
                app_name = args['form_parameters']['app_name']

      
        headers = {
                'Authorization': 'Bearer '+ token,
                'Content-Type': 'application/json',
		'User-Agent': 'SCMA'
            }

        result = {}

        if capability in ["acs_restarts"] :
            if action == "list" :
                result = list_maintenances(acs_url,stackname,headers)

        elif capability in ["acs_apps"] :
            if action == "list" :
                result = list_apps(acs_url,stackname,headers, experience)
            
            elif action == "delete" :
                status = 200
                message = ""
                apps = app_name.split(",")
                
                contain_issues = False
                deleted = 0
                for app in apps :
                    if experience == "victoria" :
                        # describe the appliation and verify that the app exists 
                        response = requests.get(acs_url+stackname+'/adminconfig/v2/apps/victoria/'+app, headers=headers, verify=False)  # nosemgrep

                        if response.status_code in [200,201,202] :
                            response = requests.delete(acs_url+stackname+'/adminconfig/v2/apps/victoria/'+app, headers=headers, verify=False)  # nosemgrep
                            if response.status_code in [200,201,202] :
                                deleted = deleted +1
                            else :
                                contain_issues = True
                        else :
                            contain_issues = True
                    
                    else : 
                        # describe the appliation and verify that the app exists 
                        response = requests.get(acs_url+stackname+'/adminconfig/v2/apps/'+app, headers=headers, verify=False)  # nosemgrep

                        if response.status_code in [200,201,202] :
                            # check if splunkbase app
                            if "splunkbaseID" in json.loads(response.text) :
                                contain_issues = True
                            else :
                                response = requests.delete(acs_url+stackname+'/adminconfig/v2/apps/'+app, headers=headers, verify=False)  # nosemgrep
                                if response.status_code in [200,201,202] :
                                    deleted = deleted +1
                                else :
                                    contain_issues = True

                        else :
                            contain_issues = True

                payload = {"deleted" : str(deleted) , "contain_issues": str(contain_issues)}
                result = {'payload': payload, 'status': 200}

        if capability in ["acs_indexes"] :
            if action == "list" :
                result = list_indexes(acs_url,stackname,headers)
            
            elif action == "add" :
                status = 200
                message = ""

                data = {}

                data["name"] = index_name

                if index_datatype != "" :
                    data["datatype"] = index_datatype
                
                if index_maxdatasize != "" :
                    data["maxDataSizeMB"] = index_maxdatasize
                
                if index_searchabledays != "" :
                    data["searchableDays"] = index_searchabledays
                
                if index_retention != "" :
                    data["SplunkArchivalRetentionDays"] = index_retention
                
                if index_storage != "" :
                    data["selfStorageBucketPath"] = index_storage
                
                response = requests.post(acs_url+stackname+'/adminconfig/v2/indexes', headers=headers,data=json.dumps(data), verify=False)  # nosemgrep

                if response.status_code in [200,201,202] :
                    logger.info("Index: "+json.dumps(data)+" added successfully")
                    message = json.loads(response.text)
                else :
                    logger.info("Error adding Index "+ json.dumps(data))
                    status = 400
                    message = json.loads(response.text)

                result = {'payload': message, 'status': status} 
            
            elif action == "delete" :
                status = 200
                message = ""
                
                response = requests.delete(acs_url+stackname+'/adminconfig/v2/indexes/'+index_name, headers=headers, verify=False)  # nosemgrep

                if response.status_code in [200,201,202] :
                    logger.info("Index "+index_name+" deleted successfully ")
                    message = "Deleted successfully"
                else :
                    logger.info("Error deleting Index  "+ index_name)
                    status = 400
                    message = json.loads(response.text)

                result = {'payload': message, 'status': status}

        elif capability in ["acs_auth"] :
            if action == "list" :
                result = list_tokens(acs_url,stackname,headers)
            
            elif action == "add" :
                status = 200
                message = ""

                data = {}
                data["user"] = token_user
                data["audience"] = token_audience
                data["expiresOn"] = token_expire
                
                headers["Authorization"] = "Basic "+base64.b64encode((token_username+":"+token_password).encode('ascii')).decode('ascii')

                response = requests.post(acs_url+stackname+'/adminconfig/v2/tokens', headers=headers,data=json.dumps(data), verify=False)  # nosemgrep

                if response.status_code in [200,201,202] :
                    logger.info("Token: "+json.dumps(data)+" added successfully")
                    message = json.loads(response.text)
                else :
                    logger.info("Error adding Token "+ json.dumps(data))
                    status = 400
                    message = json.loads(response.text)

                result = {'payload': message, 'status': status} 
            
            elif action == "delete" :
                status = 200
                message = ""
                
                data = {}
                response = requests.delete(acs_url+stackname+'/adminconfig/v2/tokens/'+token_id, headers=headers, verify=False)  # nosemgrep

                if response.status_code in [200,201,202] :
                    logger.info("Token "+token_id+" deleted successfully ")
                    message = "Deleted successfully"
                else :
                    logger.info("Error deleting Token  "+ token_id)
                    status = 400
                    message = json.loads(response.text)

                result = {'payload': message, 'status': status}

        elif capability in ["acs_outbound"] :
            if action == "list" :
                result = list_outbounds(acs_url,stackname,headers)
            
            elif action == "add" :
                status = 200
                message = ""

                data = {}
                data["outboundPorts"] = []
                data["outboundPorts"].append({"subnets": subnets.split(","), "port":int(port)})

                response = requests.post(acs_url+stackname+'/adminconfig/v2/access/outbound-ports', headers=headers,data=json.dumps(data), verify=False)  # nosemgrep

                if response.status_code in [200,201,202] :
                    logger.info("Outbounds: "+json.dumps(data["outboundPorts"][0])+" added successfully")
                    message = json.loads(response.text)
                else :
                    logger.info("Error adding Outbounds "+ json.dumps(data["outboundPorts"][0]))
                    status = 400
                    message = json.loads(response.text)

                result = {'payload': message, 'status': status} 
            
            elif action == "delete" :
                status = 200
                message = ""
                
                data = {}
                data["subnets"] = subnets.split(",")
                response = requests.delete(acs_url+stackname+'/adminconfig/v2/access/outbound-ports/'+port, headers=headers,data=json.dumps(data), verify=False)  # nosemgrep

                if response.status_code in [200,201,202] :
                    logger.info("Outbounds port configuration "+json.dumps({"subnets": subnets.split(","), "port":int(port)})+" deleted successfully ")
                    message = json.loads(response.text)
                else :
                    logger.info("Error deleting Outbounds port configuration "+json.dumps({"subnets": subnets.split(","), "port":int(port)}))
                    status = 400
                    message = json.loads(response.text)

                result = {'payload': message, 'status': status}

        elif capability in ["acs_ip"] :
            features = ["search-api","hec","s2s","search-ui","idm-ui","idm-api"]

            if feature != "*" :
                features = []
                features.append(feature)

            if action == "list" :
                result = list_subnets(features,acs_url,stackname,headers)

            elif action == "add" :
                status = 200
                message = ""
                for feat in features :
                    data = {}
                    data["subnets"] = subnets.split(",")
                    response = requests.post(acs_url+stackname+'/adminconfig/v2/access/'+feat+'/ipallowlists', headers=headers,data=json.dumps(data), verify=False)  # nosemgrep

                    if response.status_code in [200,201,202] :
                        logger.info("subnets ["+subnets+"] added successfully to "+feat)
                        message = json.loads(response.text)
                    else :
                        logger.info("Error adding subnets ["+subnets+"] to "+feat)
                        status = 400
                        message = json.loads(response.text)
                        break

                result = {'payload': message, 'status': status} 
            
            elif action == "delete" :
                status = 200
                message = ""
                for feat in features :
                    data = {}
                    data["subnets"] = subnets.split(",")
                    response = requests.delete(acs_url+stackname+'/adminconfig/v2/access/'+feat+'/ipallowlists', headers=headers,data=json.dumps(data), verify=False)  # nosemgrep

                    if response.status_code in [200,201,202] :
                        logger.info("subnets ["+subnets+"] deleted successfully from "+feat)
                        message = json.loads(response.text)
                    else :
                        logger.info("Error deleting subnets ["+subnets+"] from "+feat)
                        status = 400
                        message = json.loads(response.text)
                        break 
                result = {'payload': message, 'status': status}

        return result

    def handleStream(self, handle, in_string):
        """
        For future use
        """
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass

    def convert_to_dict(self, query):
        """
        Create a dictionary containing the parameters.
        """
        parameters = {}

        for key, val in query:

            # If the key is already in the list, but the existing entry isn't a list then make the
            # existing entry a list and add thi one
            if key in parameters and not isinstance(parameters[key], list):
                parameters[key] = [parameters[key], val]

            # If the entry is already included as a list, then just add the entry
            elif key in parameters:
                parameters[key].append(val)

            # Otherwise, just add the entry
            else:
                parameters[key] = val

        return parameters

    def parse_in_string(self, in_string):
        """
        Parse the in_string
        """

        params = json.loads(in_string)

        params['method'] = params['method'].lower()

        params['form_parameters'] = self.convert_to_dict(params.get('form', []))
        params['query_parameters'] = self.convert_to_dict(params.get('query', []))

        return params
