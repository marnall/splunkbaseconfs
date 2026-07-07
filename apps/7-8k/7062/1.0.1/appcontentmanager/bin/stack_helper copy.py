import requests
import logging
import os
import json
import sys
import logging.handlers

from splunk.persistconn.application import PersistentServerConnectionApplication
import signal
import subprocess
import tempfile
import tarfile
import re
import splunk.clilib.cli_common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

splunk_home = os.environ['SPLUNK_HOME']
LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "acms.log"

def result_errors(msg):
    return (msg["level"] == "ERROR" or  msg["level"] == "CRITICAL")

def convertResponse_to_json(response,stackname):
   
    resp = {}
    resp["stack"] = stackname
    resp["user"] = user
    resp["response"] = {}
    resp["response"]["status_code"] = response.status_code
    resp["response"]["text"] = response.text

    resp["request"] = {}
    resp["request"]["headers"] = response.request.headers.__dict__['_store']
    resp["request"]["headers"]["authorization"] = list(["Authorization","xxxxx xxxxxxx"])
    if response.request.body != None :
        resp["request"]["body"] = response.request.body 
    else :
        resp["request"]["body"] = ""
    resp["request"]["method"] = response.request.method
    resp["request"]["url"] = response.request.url

    return resp

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


def list_apps(acs_url,stackname,headers,experience,logger):
    returnVal = {}
    apps_url = acs_url+stackname+"/adminconfig/v2/apps"
    if experience in ["victoria"] :
        apps_url = apps_url+"/victoria"

    apps_url = apps_url + "?count=0"
    response = requests.get(apps_url, headers=headers)
    if response.status_code == 200 :
        resp = json.loads(response.text)
        returnVal["Private"] = resp
    
    logger.info(json.dumps(convertResponse_to_json(response, stackname)))
    return {'payload': returnVal, 'status': response.status_code}


def list_files(rest_url,stackname,headers,app, logger):
    returnVal = {}
    response = requests.get("https://"+stackname+rest_url+"/servicesNS/-/"+app+"/properties?output_mode=json&count=0",headers=headers, verify=False)
    if response.status_code == 200 :
        returnVal = json.loads(response.text)

    logger.info(json.dumps(convertResponse_to_json(response, stackname)))
    return {'payload': returnVal, 'status': response.status_code}

def list_content(rest_url,stackname,headers,app,file, logger):
    returnVal = {}
    response = requests.get("https://"+stackname+rest_url+"/servicesNS/-/"+app+"/configs/conf-"+file+"?output_mode=json&count=0",headers=headers, verify=False)
    if response.status_code == 200 :
        returnVal = [d for d in json.loads(response.text)['entry'] if d['content']['eai:appName']== app]

    logger.info(json.dumps(convertResponse_to_json(response, stackname)))
    return {'payload': returnVal, 'status': response.status_code}


class Stack_Helper(PersistentServerConnectionApplication):
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

        if 'slim.__main__' in sys.modules.keys() :
            sys.modules.pop('slim.__main__')
            sys.modules.pop('slim.partition')
            sys.modules.pop('slim.package')
            sys.modules.pop('slim.validate')
        
        import slim.__main__
        slimmain = slim.__main__.main

        acs_url = "https://admin.splunk.com/"
        rest_url = ".splunkcloud.com:8089"

        # Parse the arguments
        args = self.parse_in_string(in_string)
        
        global user
        user = args['session']['user']
        
        token = ""
        if "token" in args['form_parameters'] :
            token = args['form_parameters']['token']

        app = ""
        if "app" in args['form_parameters'] :
            app = args['form_parameters']['app']

        experience = ""
        if "experience" in args['form_parameters'] :
            experience = args['form_parameters']['experience']

        action = ""
        if "action" in args['form_parameters'] :
            action = args['form_parameters']['action']
        
        file = ""
        if "file" in args['form_parameters'] :
            file = args['form_parameters']['file']
        
        stackname = ""
        if "stackname" in args['form_parameters'] :
            stackname = args['form_parameters']['stackname']
            if "stg-" in stackname :
                acs_url = "https://staging.admin.splunk.com/"
                rest_url = ".stg.splunkcloud.com:8089"
            
            if "-shw" in stackname :
                acs_url = "https://staging.admin.splunk.com/"
                rest_url = ".stg.splunkcloud.com:8089"

            if ".stg" in stackname :
                acs_url = "https://staging.admin.splunk.com/"
                stackname = stackname.replace(".stg","")
                rest_url = ".stg.splunkcloud.com:8089"
        
        headers = {
                'Authorization': 'Bearer '+ token,
                'User-Agent': 'ACS-Helper'
            }
        
        packages_folder = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','appcontentmanager','appserver','static','packages')

        if action == "list_apps" :
            return list_apps(acs_url,stackname,headers, experience,logger)
        elif action == "list_files" :
            return list_files(rest_url,stackname,headers,app,logger)
        elif action == "list_content" :
            return list_content(rest_url,stackname,headers,app,file,logger)
        elif action == "download_app" :
            res = list_files(rest_url,stackname,headers,app,logger)
            if res['status'] == 200 :
                with tempfile.TemporaryDirectory() as tempdir:
                    os.mkdir(os.path.join(tempdir,app))
                    os.mkdir(os.path.join(tempdir,app,"default"))
                    os.mkdir(os.path.join(tempdir,app,"metadata"))
                    data_folder_created = False

                    files = res['payload']['entry']
                    for file in files :
                        if file['name'] == 'views' :
                            if not data_folder_created :
                                os.mkdir(os.path.join(tempdir,app,"default","data"))
                                os.mkdir(os.path.join(tempdir,app,"default","data","ui"))
                                os.mkdir(os.path.join(tempdir,app,"default","data","ui","views"))
                                os.mkdir(os.path.join(tempdir,app,"default","data","ui","nav"))
                                data_folder_created = True

                            res = list_content(rest_url,stackname,headers,app,file['name'],logger)
                            if res['status'] == 200 :
                                confs = res['payload']
                                for confFile in confs :
                                    # get dashboard difinition
                                    response = requests.get("https://"+stackname+rest_url+"/servicesNS/-/"+app+"/data/ui/views/"+confFile["name"]+"?output_mode=json",headers=headers, verify=False)
                                    if response.status_code == 200 :
                                        with open(os.path.join(tempdir,app,"default","data","ui","views",confFile["name"]+".xml"), "w+") as dash:
                                            r = json.loads(response.text)
                                            for d in r['entry'] :
                                                if d['acl']['app'] == app :
                                                    dash.write(d['content']['eai:data'])

                        elif file['name'] == 'nav' :
                            if not data_folder_created :
                                os.mkdir(os.path.join(tempdir,app,"default","data"))
                                os.mkdir(os.path.join(tempdir,app,"default","data","ui"))
                                os.mkdir(os.path.join(tempdir,app,"default","data","ui","views"))
                                os.mkdir(os.path.join(tempdir,app,"default","data","ui","nav"))
                                data_folder_created = True

                        else :
                            res = list_content(rest_url,stackname,headers,app,file['name'],logger)
                            if res['status'] == 200 :
                                confs = res['payload']
                                c = {}
                                for confFile in confs :
                                    #c[confFile['name']] = confFile['content']
                                    c[confFile['name']] = {k: v for k, v in confFile['content'].items() if not k.startswith('eai:') and k != "install_source_checksum"}
                                splunk.clilib.cli_common.writeConfFile(os.path.join(tempdir,app,"default",file['name']+".conf"),c)
                    
                    # generate nav 
                    if not data_folder_created :
                        os.mkdir(os.path.join(tempdir,app,"default","data"))
                        os.mkdir(os.path.join(tempdir,app,"default","data","ui"))
                        os.mkdir(os.path.join(tempdir,app,"default","data","ui","views"))
                        os.mkdir(os.path.join(tempdir,app,"default","data","ui","nav"))
                        data_folder_created = True
                    
                    response = requests.get("https://"+stackname+rest_url+"/servicesNS/-/"+app+"/data/ui/nav?output_mode=json",headers=headers, verify=False)
                    if response.status_code == 200 :
                        with open(os.path.join(tempdir,app,"default","data","ui","nav","default.xml"), "w+") as nav:
                            r = json.loads(response.text)
                            for n in r['entry'] :
                                if n['acl']['app'] == app :
                                    nav.write(n['content']['eai:data'])

                    # generate a default.meta conf file
                    meta = {}
                    meta[''] = {}
                    meta['']["access"] = 'read : [ * ], write : [ admin ]'
                    meta['']["export"] = 'system'
                    splunk.clilib.cli_common.writeConfFile(os.path.join(tempdir,app,"metadata","default.meta"),meta)

                    # package the app to appserver/static/packages folder
                
                    argv = []
                    argv.append(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))
                    argv.append("package")

                    argv.append(os.path.join(tempdir,app))
                    argv.append("-o")
                    argv.append(packages_folder)
                    results = slimmain(argv)

                    apppath = ""
                    apppath = results[-1]["msg"].replace('Source package exported to  "','').replace('"','')
                    os.rename(apppath,apppath.replace("tar.gz","spl"))
                    return {'payload': {'path' : apppath.replace("tar.gz","spl")}, 'status': 200}
                            

            
        return {'payload': "", 'status': 200}

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
