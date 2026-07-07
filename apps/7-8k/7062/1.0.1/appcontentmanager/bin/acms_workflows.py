import requests
import logging
import os
import json
import sys
import logging.handlers

from splunk.persistconn.application import PersistentServerConnectionApplication
import signal
import subprocess
import uuid
import base64

import re

import tempfile
import tarfile
import time
import shutil
from importlib import reload

import splunk.clilib.cli_common
import splunk.rest as rest
from urllib.parse import unquote

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import splunklib.client as client

class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout


workflow = ""
jobid = ""
user = ""
action = ""
jobname = ""
actiontype = ""

splunk_home = os.environ['SPLUNK_HOME']
LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "acms.log"

def result_errors(msg):
    return (msg["level"] == "ERROR" or  msg["level"] == "CRITICAL")

def processing_inspection(req):
    return (req["status"] == "PROCESSING")

def contain_errors(req):
    return (req["status"] != "SUCCESS")

def vetted_apps(req):
    return (req["status"] == "SUCCESS")

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

def convertResponse_to_json(response,currAction="",step="",stack=None):
    
    resp = {}
    resp["mode"] = action
    resp["action"] = currAction
    
    if stack == None :
        resp["workflow"] = workflow
    else :
        resp["stack"] = stack

    resp["user"] = user
    resp["jobid"] = jobid
    resp["jobname"] = jobname
    resp["step"] = step
    resp["response"] = {}

    if type(response) == dict :
        resp["response"]["status_code"] = response['status_code']
        resp["response"]["text"] = response['text']
    else :
        resp["response"]["status_code"] = response.status_code
        if currAction == "report" :
            resp["response"]["text"] = ""
        else :
            resp["response"]["text"] = response.text
        resp["request"] = {}
        resp["request"]["headers"] = response.request.headers.__dict__['_store']
        if response.request.body != None :
            if type(response.request.body) == bytes :
                resp["request"]["body"] = "<<binary object>>"
            else :
                resp["request"]["body"] = response.request.body 

        else :
            resp["request"]["body"] = ""
        
        resp["request"]["method"] = response.request.method
        resp["request"]["url"] = response.request.url
        resp["request"]["headers"]["authorization"] = list(["Authorization","xxxxx xxxxxxx"])

    return resp


def create_new_log(logger,mode,action,step,workflow_name,status,message):
    resp = {}
    resp["type"] = actiontype
    resp["mode"] = mode
    resp["action"] = action
    resp["step"] = step
    resp["workflow"] = workflow_name
    resp["user"] = user
    resp["jobid"] = jobid
    resp["jobname"] = jobname
    resp["response"] = {}
    resp["response"]['status_code'] = status
    resp["response"]["text"] = message
    time.sleep(1)
    logger.info(json.dumps(resp))

def pushContentToRepo(logger,workflow,repo,app,branch,filename,token,comment,content):
    url="https://api.github.com/repos/"+repo+"/"+app+"/contents/"+filename
    base64content=base64.b64encode(bytes(content, 'utf-8'))
    data = requests.get(url+'?ref='+branch, headers = {"Authorization": "token "+token}).json()

    if 'sha' in data :
        sha = data['sha']
        if base64content.decode('utf-8')+"\n" != data['content']:
            message = json.dumps({"message":comment,"branch": branch,"content": base64content.decode("utf-8") ,"sha": sha })
            resp=requests.put(url, data = message, headers = {"Content-Type": "application/json", "Authorization": "token "+token})
            if resp.status_code in [200, 201, 202] :
                create_new_log(logger,'workflow',"push","Push file content {} to repo {} ...".format(filename, repo+"/"+app),workflow,200,resp.text)
            else :
                create_new_log(logger,'workflow',"push","Push file content {} to repo {} ...".format(filename, repo+"/"+app),workflow,resp.status_code,resp.text)
        else:
            create_new_log(logger,'workflow',"push","Push file content {} to repo {} ...".format(filename, repo+"/"+app),workflow,500,"No diffs for the file {} to push.".format(filename))
    else :
        create_new_log(logger,'workflow',"push","Push file content {} to repo {} ...".format(filename, repo+"/"+app),workflow,500,"the file {} does not exists in the repo {} , branch {}".format(filename,repo,branch))

class ACMS_Workflows(PersistentServerConnectionApplication):
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

        logger = setup_logger()
        

        #dbg.set_breakpoint()
        if 'slim.__main__' in sys.modules.keys() :
            sys.modules.pop('slim.__main__')
            sys.modules.pop('slim.partition')
            sys.modules.pop('slim.package')
            sys.modules.pop('slim.validate')
        
        import slim.__main__
        slimmain = slim.__main__.main
        # import dynamically slim package 
        
        # Parse the arguments
        args = self.parse_in_string(in_string)
        
        global user
        global jobid
        global jobname
        global workflow
        global action
        global actiontype

        user = args['session']['user']
        isscheduling = False
        contents = {}
        wkf = {}
        contentaction = ''

        ####################
        deployanyway = False
        confoverride = False
        mergelocal = False
        confowner = "nobody"
        splunku= None
        splunkp=None
        upgradeapp = False
        ####################
       

        if "splunku" in args['form_parameters'] :
            if isscheduling :
                splunku = unquote(args['form_parameters']['splunku'])
            else :
                splunku = args['form_parameters']['splunku']
            
        
        if "splunkp" in args['form_parameters'] :
            if isscheduling :
                splunkp = unquote(args['form_parameters']['splunkp'])
            else :
                splunkp = args['form_parameters']['splunkp']

        if "confowner" in args['form_parameters'] :
            confowner = args['form_parameters']['confowner']

        if "mergelocal" in args['form_parameters'] :
            mergelocal = args['form_parameters']['mergelocal'] == "true"

        if "contents" in args['form_parameters'] :
            if isscheduling :
                contents = json.loads(unquote(args['form_parameters']['contents']))
            else :
                contents = json.loads(args['form_parameters']['contents'])
        
        if "jobid" in args['form_parameters'] :
            if isscheduling :
                jobid = unquote(args['form_parameters']['jobid'])
            else :
                jobid = args['form_parameters']['jobid']
        
        if "jobname" in args['form_parameters'] :
            if isscheduling :
                jobname = unquote(args['form_parameters']['jobname'])
            else :
                jobname = args['form_parameters']['jobname']
        
        if "workflow" in args['form_parameters'] :
            if isscheduling :
                wkf = json.loads(unquote(args['form_parameters']['workflow']))
            else :
                wkf = json.loads(args['form_parameters']['workflow'])
        
        if "contentaction" in args['form_parameters'] :
            if isscheduling :
                contentaction = unquote(args['form_parameters']['contentaction'])
            else :
                contentaction = args['form_parameters']['contentaction']
        
        if "deployanyway" in args['form_parameters'] :
            if isscheduling :
                deployanyway = unquote(args['form_parameters']['deployanyway']) == "true"
            else :
                deployanyway = args['form_parameters']['deployanyway'] == "true"

        if "upgradeapp" in args['form_parameters'] :
            if isscheduling :
                upgradeapp = unquote(args['form_parameters']['upgradeapp']) == "true"
            else :
                upgradeapp = args['form_parameters']['upgradeapp'] == 'true'
        
        if "confoverride" in args['form_parameters'] :
            if isscheduling :
                confoverride = unquote(args['form_parameters']['confoverride']) == "true"
            else :
                confoverride = args['form_parameters']['confoverride'] == "true"



        reports_folder = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','appcontentmanager','appserver','static','reports')
        packages_folder = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','appcontentmanager','appserver','static','packages')

        if not os.path.exists(reports_folder) :
            os.mkdir(reports_folder)

        if not os.path.exists(packages_folder) :
            os.mkdir(packages_folder)

        actions = []
        stacks = []

        service = client.Service(token=args['session']["authtoken"],host="127.0.0.1", port=8089)
        storage_passwords = service.storage_passwords

        for act in wkf['actions'] :
            try :
                response, content = rest.simpleRequest("/servicesNS/nobody/appcontentmanager/configs/conf-acms_actions/"+act+"?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False, timeout=None)
                if response.status in [200,201,202]:
                    act = json.loads(content)['entry'][0]
                    actions.append(act)
                    create_new_log(logger,'workflow',"workflow_step",'Loading action {} definition.'.format(act['name']),wkf['name'],200,'successfully loaded action {} definition.'.format(act['name']))
                    if act['content']['type'] == 'deploy' :
                        for s in act['content']['stacks'].split(","):
                            if s not in stacks :
                                stacks.append(s)
                    
                else :
                    create_new_log(logger,'workflow',"workflow_step",'Loading action {} definition.'.format(act['name']),wkf['name'],500,'Error loading action {} definition.'.format(act['name']))
                    
            except :
                logger.info("error loading action: "+act['name'])
        
        for action in actions:
            actiontype = action['content']['type']
            if action['content']['type'] == 'save' :
                create_new_log(logger,'workflow',"workflow_step","Start SAVE action {}".format(action['content']['title']),wkf['name'],200,"Start SAVE action {}".format(action['content']['title']))
                time.sleep(1)
                sessionID = None
                with tempfile.TemporaryDirectory() as tempdir:
                    if os.path.exists(action['content']['path']) :
                        if contentaction == 'exportall' :
                            for app in contents :
                                if app['type'] == "private" :
                                    if mergelocal :
                                        # package the app using splunk package endpoint to merge local and default
                                        headers={'authorization' : "Splunk %s" % args['session']["authtoken"]}
                                        response, content = rest.simpleRequest('/services/apps/local/'+app["name"]+'/package?output_mode=json&count=0', sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False, timeout=None)
                                        if response.status in [200,201,202]:

                                            tar = tarfile.open(os.path.join(splunk_home,"share","splunk","app_packages",app["name"]+".spl"))

                                            tar.extractall(tempdir)
                                            
                                            # remove local metadata file
                                            if os.path.exists(os.path.join(tempdir,app["name"],"metadata","local.meta")):
                                                os.remove(os.path.join(tempdir,app["name"],"metadata","local.meta"))
                                            
                                            # remove manifest file
                                            if os.path.exists(os.path.join(tempdir,app["name"],"app.manifest")):
                                                os.remove(os.path.join(tempdir,app["name"],"app.manifest"))

                                            argv = []
                                            argv.append(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))
                                            argv.append("package")

                                            argv.append(os.path.join(tempdir,app["name"]))
                                            argv.append("-o")
                                            argv.append(tempdir)
                                            
                                            results = slimmain(argv)
                                            source_package = results[-1]["msg"].replace('Source package exported to  "','').replace('"','')

                                            if os.path.isfile(os.path.join(action['content']['path'],os.path.split(source_package)[1])):   
                                                os.remove(os.path.join(action['content']['path'],os.path.split(source_package)[1]))

                                            shutil.move(source_package,action['content']['path'])
                                            time.sleep(1)
                                            create_new_log(logger,'workflow',"save","Save application {} content".format(app["name"]),wkf['name'],200,"Application {} saved in {}.".format(app["name"],action['content']['path']))
                                        else :
                                            create_new_log(logger,'workflow',"save","Save application {} content".format(app["name"]),wkf['name'],500,"{} application not installed locally.".format(app["name"]))
                                    else :

                                        try :
                                            # no merge, create a copy of the app and then remove local folder
                                            shutil.copytree(os.path.join(splunk_home,"etc","apps",app["name"]),os.path.join(tempdir,app["name"]))
                                            
                                            if os.path.exists(os.path.join(tempdir,app["name"],"local")) :
                                                shutil.rmtree(os.path.join(tempdir,app["name"],"local"))
                                            
                                            # remove local metadata file
                                            if os.path.exists(os.path.join(tempdir,app["name"],"metadata","local.meta")):
                                                os.remove(os.path.join(tempdir,app["name"],"metadata","local.meta"))
                                            
                                            # remove manifest file
                                            if os.path.exists(os.path.join(tempdir,app["name"],"app.manifest")):
                                                os.remove(os.path.join(tempdir,app["name"],"app.manifest"))

                                            argv = []
                                            argv.append(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))
                                            argv.append("package")

                                            argv.append(os.path.join(tempdir,app["name"]))
                                            #sys.argv.append("/Users/akouki/Documents/Splunks/9.1.1/splunk/etc/apps/splunk_app_for_nix")
                                            argv.append("-o")
                                            argv.append(tempdir)
                                            
                                            results = slimmain(argv)
                                            source_package = results[-1]["msg"].replace('Source package exported to  "','').replace('"','')

                                            if os.path.isfile(os.path.join(action['content']['path'],os.path.split(source_package)[1])):   
                                                os.remove(os.path.join(action['content']['path'],os.path.split(source_package)[1]))

                                            shutil.move(source_package,action['content']['path'])
                                            create_new_log(logger,'workflow',"save","Save application {} content".format(app["name"]),wkf['name'],200,"Application {} saved in {}.".format(app["name"],action['content']['path']))
                                        except :
                                            create_new_log(logger,'workflow',"save","Save application {} content".format(app["name"]),wkf['name'],500,"{} application not installed locally.".format(app["name"]))
                                elif app['type'] == "splunkbase" :
                                    try :
                                        if sessionID == None :
                                            login_url = "https://splunkbase.splunk.com/api/account:login/"
                                            payload = {
                                                'username': splunku,
                                                'password': splunkp
                                            }

                                            response = requests.post(login_url, data=payload)
                                            if response.status_code == 200:
                                                sessionID = response.cookies.get_dict()
                                                create_new_log(logger,'workflow',"login","Login: Splunkbase session ID successfully retrieved.",wkf['name'],200,"")
                                            else :
                                                sessionID = ''
                                                create_new_log(logger,'workflow',"login","Login: Failure to retrieve Splunkbase session ID.",wkf['name'],500,"Error downloading application {} from splunkbase. Error generating a session id. please verify your splunk.com username and password.".format(app["name"]))
                                        
                                        if sessionID != '':
                                            version = app['version']
                                            if version == ""  :
                                                url = "https://splunkbase.splunk.com/api/v1/app/"+app['uid']+"/release/"
                                                response = requests.get(url, cookies=sessionID)
                                                if response.status_code == 200:
                                                    d = response.json()
                                                    version = d[0]['name']
                                                    file_name = app['name']+"_"+version+".tgz"
                                                    if os.path.isfile(os.path.join(action['content']['path'],file_name)):   
                                                        os.remove(os.path.join(action['content']['path'],file_name))
                                                    
                                                    download_url = "http://splunkbase.splunk.com/app/"+app['uid']+"/release/"+version+"/download/"
                                                    response = requests.get(download_url, cookies=sessionID)
                                                    if response.status_code == 200:
                                                        create_new_log(logger,'workflow',"save","Download application {} from Splunkbase".format(app["name"]),wkf['name'],200,"Application {} downloaded successfully from splunkbase to {}.".format(app["name"],action['content']['path']))
                                                        with open(os.path.join(action['content']['path'],file_name), 'wb') as file:
                                                            file.write(response.content)
                                                    else :
                                                        create_new_log(logger,'workflow',"save","Download application {} from Splunkbase".format(app["name"]),wkf['name'],500,"Error downloading application {} from splunkbase to {}.".format(app["name"],action['content']['path']))
                                                    
                                                else :
                                                    create_new_log(logger,'workflow',"save","Download application {} from Splunkbase".format(app["name"]),wkf['name'],500,"Error downloading application {} from splunkbase to {}.".format(app["name"],action['content']['path']))
                                            
                                            else :
                                                file_name = app['name']+"_"+version+".tgz"
                                                if os.path.isfile(os.path.join(action['content']['path'],file_name)):   
                                                    os.remove(os.path.join(action['content']['path'],file_name))
                                                
                                                download_url = "http://splunkbase.splunk.com/app/"+app['uid']+"/release/"+version+"/download/"
                                                response = requests.get(download_url, cookies=sessionID)
                                                if response.status_code == 200:
                                                    create_new_log(logger,'workflow',"save","Download application {} from Splunkbase".format(app["name"]),wkf['name'],200,"Application {} downloaded successfully from splunkbase to {}.".format(app["name"],action['content']['path']))
                                                    with open(os.path.join(action['content']['path'],file_name), 'wb') as file:
                                                        file.write(response.content)
                                                else :
                                                    create_new_log(logger,'workflow',"save","Download application {} from Splunkbase".format(app["name"]),wkf['name'],500,"Error downloading application {} from splunkbase to {}.".format(app["name"],action['content']['path']))


                                    except :
                                        create_new_log(logger,'workflow',"save","Download application {} from Splunkbase".format(app["name"]),wkf['name'],500,"Error downloading application {} from splunkbase to {}.".format(app["name"],action['content']['path']))

                                elif app['type'] == "upload" :
                                    try :
                                        if os.path.isfile(os.path.join(action['content']['path'],app['name'])):   
                                            os.remove(os.path.join(action['content']['path'],app['name']))

                                        shutil.copy(os.path.join(packages_folder,app['name']),action['content']['path'])
                                        create_new_log(logger,'workflow',"save","Save application {} content".format(app["name"]),wkf['name'],200,"Application {} saved in {}.".format(app["name"],action['content']['path']))
                                    except :
                                        create_new_log(logger,'workflow',"save","Save application {} content".format(app["name"]),wkf['name'],500,"Error saving application {} to {}.".format(app["name"],action['content']['path']))

                        elif contentaction == 'takeaslice' :
                            try :
                                for app in contents :
                                    source_package = app.strip()
                                    appName = os.path.split(source_package)[1]

                                    if os.path.isfile(os.path.join(action['content']['path'],os.path.split(source_package)[1])):   
                                        os.remove(os.path.join(action['content']['path'],os.path.split(source_package)[1]))

                                    shutil.move(source_package,action['content']['path'])
                                    create_new_log(logger,'workflow',"save","Save application {} content".format(appName),wkf['name'],200,"Application {} saved in {}.".format(appName,action['content']['path']))
                            except :
                                create_new_log(logger,'workflow',"save","Save application {} content".format(app["name"]),wkf['name'],500,"{} application not installed locally.".format(app["name"]))
                            
                        elif contentaction == 'buildyourapp' :
                            try :
                                source_package = contents
                                app = {}
                                app["name"] = os.path.split(source_package)[1]

                                if os.path.isfile(os.path.join(action['content']['path'],os.path.split(source_package)[1])):   
                                    os.remove(os.path.join(action['content']['path'],os.path.split(source_package)[1]))

                                shutil.move(source_package,action['content']['path'])
                                create_new_log(logger,'workflow',"save","Save application {} content".format(app["name"]),wkf['name'],200,"Application {} saved in {}.".format(app["name"],action['content']['path']))

                            except :
                                create_new_log(logger,'workflow',"save","Save application {} content".format(app["name"]),wkf['name'],500,"{} application not installed locally.".format(app["name"]))
                            
                        elif contentaction == 'patchmode' :
                            try :
                                # save dashboards
                                for content in contents.keys() :
                                    c = content.split("###")
                                    app = c[0]
                                    file = c[1]
                                    stanza = c[2]
                                    app_folder = os.path.join(action['content']['path'],app)
                                    if not os.path.exists(app_folder) :
                                        os.mkdir(app_folder)

                                    if file == "views" :
                                        response, content = rest.simpleRequest("/servicesNS/"+args['session']['user']+"/"+app+"/data/ui/views/"+stanza+"?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False, timeout=None)
                                        if response.status in [200,201,202]:
                                            content = json.loads(content)['entry'][0]['content']['eai:data']
                                            with open(os.path.join(app_folder,stanza+".xml"),"w+") as dash :
                                                dash.write(content)
                                            
                                            create_new_log(logger,'workflow',"save","Save {} content".format(file+".xml"),wkf['name'],200,"Dashboard {} saved in {}.".format(stanza,action['content']['path']))

                                            
                                    #save Navigation
                                    elif file == "nav" :
                                        response, content = rest.simpleRequest("/servicesNS/"+args['session']['user']+"/"+app+"/data/ui/nav?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False, timeout=None)
                                        if response.status in [200,201,202]:
                                            content = json.loads(content)['entry'][0]['content']['eai:data']
                                            with open(os.path.join(app_folder,"default.xml"),"w+") as dash :
                                                dash.write(content)
                                            
                                            create_new_log(logger,'workflow',"save","Save default.xml nav content".format(file+".xml"),wkf['name'],200,"Navigation default.xml saved in {}.".format(action['content']['path']))

                                    else :
                                        with open(os.path.join(app_folder,file+".conf"),"a+") as conf :
                                            conf.write("\n["+stanza+"]\n")
                                            for att in contents[content].keys() :
                                                val = ''
                                                if type(contents[content][att]) == type(True) :
                                                    val = str(int(contents[content][att] == True))
                                                else :
                                                    val = str(contents[content][att])

                                                conf.write(att+"="+val+"\n")
                                            time.sleep(1)
                                            create_new_log(logger,'workflow',"save","Save stanza {} in {}.conf in app: {} ".format(stanza,file,app),wkf['name'],200,"Saved successfully in {}.".format(action['content']['path']))
                                        
                            except Exception as e:
                                
                                create_new_log(logger,'workflow',"save","Save configurations file {}.conf".format(file),wkf['name'],500,"Error saving configuration file {}.conf .".format(file))
                            
                    else :
                        create_new_log(logger,'workflow',"workflow_step","save","Path not found: "+action['content']['path'],wkf['name'],500,"Path not found: "+action['content']['path'])

                create_new_log(logger,'workflow',"terminated","Action execution completed",wkf['name'],200,"Action execution completed")

            elif action['content']['type'] == 'push' :
                create_new_log(logger,'workflow',"workflow_step","Start PUSH action {}".format(action['content']['title']),wkf['name'],200,"Start PUSH action {}".format(action['content']['title']))
                if contentaction in ['buildyourapp','takeaslice', 'exportall'] :
                    create_new_log(logger,'workflow',"push","Not supported Action.",wkf['name'],500,"Push content to configurations is only compatible with the Patch mode.")
                elif contentaction == 'patchmode' :

                    doneConfs = []

                    for content in contents.keys() :
                        c = content.split("###")
                        app = c[0]
                        file = c[1]
                        stanza = c[2]
                        toWrite = ''
                        filename = ''
                        if file in ["views", "nav"] :
                            if file == "views" :
                                response, content = rest.simpleRequest("/servicesNS/"+args['session']['user']+"/"+app+"/data/ui/views/"+stanza+"?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False, timeout=None)
                                if response.status in [200,201,202]:
                                    toWrite = json.loads(content)['entry'][0]['content']['eai:data']
                                    filename = 'default/data/ui/views/'+stanza+".xml"
                            elif file == "nav" :
                                response, content = rest.simpleRequest("/servicesNS/"+args['session']['user']+"/"+app+"/data/ui/nav?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False, timeout=None)
                                if response.status in [200,201,202]:
                                    toWrite = json.loads(content)['entry'][0]['content']['eai:data']
                                    filename = "default/data/ui/nav/default.xml"
                            
                            pushContentToRepo(logger,wkf['name'],action['content']['repo'],app,action['content']['branch'],filename,action['content']['token'],action['content']['comment'],toWrite)
                        
                        else :
                            key = app+"###"+file

                            if key not in doneConfs :
                                doneConfs.append(key)
                                response, content = rest.simpleRequest("/servicesNS/"+args['session']['user']+"/"+app+"/configs/conf-"+file+"?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False, timeout=None)
                                if response.status in [200,201,202]:
                                    filename = "default/"+file+".conf"

                                    content = json.loads(content)['entry']
                                    for stanza in content :
                                        if stanza['acl']['app'] == app :
                                            toWrite = toWrite+"\n["+stanza['name']+"]\n"
                                            for att in stanza['content'].keys() :
                                                val = ''
                                                if type(stanza['content'][att]) == type(True) :
                                                    val = str(int(stanza['content'][att] == True))
                                                else :
                                                    val = str(stanza['content'][att])
                                                toWrite = toWrite+att+"="+val+"\n"
                                    
                                    pushContentToRepo(logger,wkf['name'],action['content']['repo'],app,action['content']['branch'],filename,action['content']['token'],action['content']['comment'],toWrite)
                                
                        
                        

                create_new_log(logger,'workflow',"terminated","Action execution completed",wkf['name'],200,"Action execution completed")
            elif action['content']['type'] == 'inspect' :
                create_new_log(logger,'workflow',"workflow_step","Start INSPECT action {}".format(action['content']['title']),wkf['name'],200,"Start INSPECT action {}".format(action['content']['title']))
                tags = action['content']['tags'].split(",")
                time.sleep(1)
                if contentaction == 'patchmode' :
                    create_new_log(logger,'workflow',"inspect","Not supported Action.",wkf['name'],500,"Inspection action not compatible with patch mode.")
                elif contentaction == 'buildyourapp' :
                    source_package = contents
                    app = {}
                    app["name"] = source_package.split("/")[-1]
                    app["path"] = source_package
                    progress_inspection = []
                    #get Token from appinspect
                    appinspectToken = ""
                    r = requests.get('https://api.splunk.com/2.0/rest/login/splunk', verify=False,auth=(splunku, splunkp))
                    if r.status_code == 200:
                        create_new_log(logger,'workflow',"login","Generate AppInspet Token...",wkf['name'],200,"")
                        appinspectToken = r.json()["data"]["token"]
                    
                        base_url = "https://appinspect.splunk.com"
                        validate_url = base_url + "/v1/app/validate"

                        file_handler = open(source_package, "rb")
                        files = {'app_package': file_handler}
                        fields = {'included_tags': tags }
                        
                        headers = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all"}
                        valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)
                        
                        file_handler.close()
                        valresponse_json = {}
                        valresponse_json = valresponse.json()

                        request_id = valresponse_json['request_id']
                        progress_inspection.append({"app":app["name"], "status" : "PROCESSING", 'request_id' :request_id , "path" : source_package})

                        while len(list(filter(processing_inspection,progress_inspection))) > 0 :
                            time.sleep(10)
                            for request in progress_inspection :

                                if request['status'] == "PROCESSING" :

                                    status_url = base_url + "/v1/app/validate/status/"+request["request_id"]

                                    valresponse = requests.get( status_url, verify=False, headers=headers)
                                    
                                    valresponse_json = valresponse.json()

                                    status = 'FAILURE'
                                    if valresponse_json['status'] ==  "SUCCESS" :
                                        # save report 
                                        header_report = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all", "Content-Type": "text/html"}
                                        report_url = base_url + "/v1/app/report/"+request["request_id"]
                                        reportresponse = requests.request("GET", report_url, verify=False, headers=header_report)
                                        o = open(os.path.join(reports_folder,request["app"] + "_" + jobid+".html"),"w+")
                                        o.write(reportresponse.content.decode('utf-8'))

                                        if valresponse_json['info']["error"] == 0 and valresponse_json['info']["failure"] == 0 and valresponse_json['info']["manual_check"] == 0 :
                                            status = 'SUCCESS'
                                    elif valresponse_json['status'] ==  "PROCESSING" :
                                        status = "PROCESSING"
                                    
                                    request['status'] = status
                                    
                                    if status != "PROCESSING" :
                                        if status != "SUCCESS" :
                                            valresponse.status_code = 406
                                            reportresponse.status_code = 406
                                        
                                        create_new_log(logger,'workflow',"inspect",'Application {} Inspected [result: {}]'.format(request["app"],status),wkf['name'],valresponse.status_code,"")
                                        time.sleep(1)
                                        create_new_log(logger,'workflow',"report",'Inspection report for Application {} Downloaded'.format(request["app"]),wkf['name'],valresponse.status_code,"")

                    else :
                        create_new_log(logger,'workflow',"login","Generate AppInspet Token...",wkf['name'],500,"Error while retrieving AppInspect token : "+valresponse.text)

                elif contentaction == "takeaslice" :
                    progress_inspection = []

                    #get Token from appinspect
                    appinspectToken = ""
                    r = requests.get('https://api.splunk.com/2.0/rest/login/splunk', verify=False,auth=(splunku, splunkp))
                    
                    if r.status_code == 200:
                        create_new_log(logger,'workflow',"login","Generate AppInspet Token...",wkf['name'],200,"")
                        appinspectToken = r.json()["data"]["token"]
                    
                        base_url = "https://appinspect.splunk.com"
                        validate_url = base_url + "/v1/app/validate"

                        for app in contents :
                            source_package = app.strip()
                            appName = os.path.split(source_package)[1]

                            file_handler = open(source_package, "rb")
                            files = {'app_package': file_handler}
                            fields = {'included_tags': tags }
                            
                            headers = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all"}
                            valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)
                            
                            file_handler.close()
                            valresponse_json = {}
                            valresponse_json = valresponse.json()
                            
                            
                            create_new_log(logger,'workflow',"inspect",'Submit application {} to AppInspect'.format(appName),wkf['name'],200,"")

                            request_id = valresponse_json['request_id']
                            progress_inspection.append({"app":appName, "status" : "PROCESSING", 'request_id' :request_id , "path" : source_package})
                        
                        while len(list(filter(processing_inspection,progress_inspection))) > 0 :
                            time.sleep(10)
                            for request in progress_inspection :

                                if request['status'] == "PROCESSING" :

                                    status_url = base_url + "/v1/app/validate/status/"+request["request_id"]

                                    valresponse = requests.get( status_url, verify=False, headers=headers)
                                    
                                    valresponse_json = valresponse.json()

                                    status = 'FAILURE'
                                    if valresponse_json['status'] ==  "SUCCESS" :
                                        # save report 
                                        header_report = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all", "Content-Type": "text/html"}
                                        report_url = base_url + "/v1/app/report/"+request["request_id"]
                                        reportresponse = requests.request("GET", report_url, verify=False, headers=header_report)
                                        o = open(os.path.join(reports_folder,request["app"] + "_" + jobid+".html"),"w+")
                                        o.write(reportresponse.content.decode('utf-8'))

                                        if valresponse_json['info']["error"] == 0 and valresponse_json['info']["failure"] == 0 and valresponse_json['info']["manual_check"] == 0 :
                                            status = 'SUCCESS'
                                    elif valresponse_json['status'] ==  "PROCESSING" :
                                        status = "PROCESSING"
                                    
                                    request['status'] = status
                                    
                                    if status != "PROCESSING" :
                                        if status != "SUCCESS" :
                                            valresponse.status_code = 406
                                            reportresponse.status_code = 406
                                        
                                        create_new_log(logger,'workflow',"inspect",'Application {} Inspected [result: {}]'.format(request["app"],status),wkf['name'],valresponse.status_code,"")
                                        time.sleep(1)
                                        create_new_log(logger,'workflow',"report",'Inspection report for Application {} Downloaded'.format(request["app"]),wkf['name'],valresponse.status_code,"")

                                        
                    else :
                        create_new_log(logger,'workflow',"login","Generate AppInspet Token...",wkf['name'],500,"Error while retrieving AppInspect token : "+valresponse.text)          

                elif contentaction == "exportall" :

                    # verify that there is at least one private app
                    private_apps = next((app for app in contents if app['type'] in ["private","upload"]), None)
                    splunkbase_apps = next((app for app in contents if app['type'] == "splunkbase"), None)
                    
                    with tempfile.TemporaryDirectory() as tempdir:

                        if private_apps != None :
                            progress_inspection = []

                            #get Token from appinspect
                            appinspectToken = ""
                            r = requests.get('https://api.splunk.com/2.0/rest/login/splunk', verify=False,auth=(splunku, splunkp))
                            
                            
                            if r.status_code == 200:
                                create_new_log(logger,'workflow',"login","Generate AppInspet Token...",wkf['name'],200,"")
                                appinspectToken = r.json()["data"]["token"]
                            
                                base_url = "https://appinspect.splunk.com"
                                validate_url = base_url + "/v1/app/validate"

                                for app in contents :

                                    if app["type"] == "private" :

                                        if mergelocal :
                                            # package the app using splunk package endpoint to merge local and default
                                            headers={'authorization' : "Splunk %s" % args['session']["authtoken"]}
                                            response, content = rest.simpleRequest('/services/apps/local/'+app["name"]+'/package?output_mode=json', sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False, timeout=None)

                                            if response.status in [200,201,202]:
                                                tar = tarfile.open(os.path.join(splunk_home,"share","splunk","app_packages",app["name"]+".spl"))

                                                tar.extractall(tempdir)
                                                
                                                # remove local metadata file
                                                if os.path.exists(os.path.join(tempdir,app["name"],"metadata","local.meta")):
                                                    os.remove(os.path.join(tempdir,app["name"],"metadata","local.meta"))
                                                
                                                # remove manifest file
                                                if os.path.exists(os.path.join(tempdir,app["name"],"app.manifest")):
                                                    os.remove(os.path.join(tempdir,app["name"],"app.manifest"))

                                                argv = []
                                                argv.append(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))
                                                argv.append("package")

                                                argv.append(os.path.join(tempdir,app["name"]))
                                                argv.append("-o")
                                                argv.append(tempdir)
                                                
                                                results = slimmain(argv)
                                                package_errors = list(filter(result_errors,results))
                                                
                                                create_new_log(logger,'workflow',"package","Package application {}".format(app["name"]),wkf['name'],200,"")
                                                source_package = results[-1]["msg"].replace('Source package exported to  "','').replace('"','')

                                                file_handler = open(source_package, "rb")
                                                files = {'app_package': file_handler}
                                                fields = {'included_tags': tags }
                                                
                                                headers = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all"}
                                                valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)
                                                
                                                file_handler.close()
                                                valresponse_json = {}
                                                valresponse_json = valresponse.json()
                                                
                                                create_new_log(logger,'workflow',"inspect",'Submit application {} to AppInspect'.format(app["name"]),wkf['name'],200,"")
                                                
                                                request_id = valresponse_json['request_id']

                                                progress_inspection.append({"app":app["name"], "status" : "PROCESSING", 'request_id' :request_id , "path" : source_package})

                                                tar.close()
                                            
                                        else :
                                            # no merge, create a copy of the app and then remove local folder
                                            shutil.copytree(os.path.join(splunk_home,"etc","apps",app["name"]),os.path.join(tempdir,app["name"]))
                                            
                                            if os.path.exists(os.path.join(tempdir,app["name"],"local")) :
                                                shutil.rmtree(os.path.join(tempdir,app["name"],"local"))
                                            
                                            # remove local metadata file
                                            if os.path.exists(os.path.join(tempdir,app["name"],"metadata","local.meta")):
                                                os.remove(os.path.join(tempdir,app["name"],"metadata","local.meta"))
                                            
                                            # remove manifest file
                                            if os.path.exists(os.path.join(tempdir,app["name"],"app.manifest")):
                                                os.remove(os.path.join(tempdir,app["name"],"app.manifest"))

                                            argv = []
                                            argv.append(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))
                                            argv.append("package")

                                            argv.append(os.path.join(tempdir,app["name"]))
                                            #sys.argv.append("/Users/akouki/Documents/Splunks/9.1.1/splunk/etc/apps/splunk_app_for_nix")
                                            argv.append("-o")
                                            argv.append(tempdir)
                                            
                                            results = slimmain(argv)
                                                                                        
                                            create_new_log(logger,'workflow',"package","Package application {}".format(app["name"]),wkf['name'],200,"")
                                            source_package = results[-1]["msg"].replace('Source package exported to  "','').replace('"','')

                                            file_handler = open(source_package, "rb")
                                            files = {'app_package': file_handler}
                                            fields = {'included_tags': tags }
                                            
                                            headers = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all"}
                                            valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)
                                            
                                            file_handler.close()
                                            valresponse_json = {}
                                            valresponse_json = valresponse.json()
                                            
                                            create_new_log(logger,'workflow',"inspect",'Submit application {} to AppInspect'.format(app["name"]),wkf['name'],200,"")
                                            
                                            request_id = valresponse_json['request_id']

                                            progress_inspection.append({"app":app["name"], "status" : "PROCESSING", 'request_id' :request_id , "path" : source_package})

                                    elif app["type"] == "upload" :
                                        # package the app using splunk package endpoint to merge local and default
                                        source_package = os.path.join(packages_folder,app["name"])

                                        file_handler = open(source_package, "rb")
                                        files = {'app_package': file_handler}
                                        fields = {'included_tags': tags }
                                        
                                        headers = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all"}
                                        valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)
                                        
                                        file_handler.close()
                                        valresponse_json = {}
                                        valresponse_json = valresponse.json()
                                        
                                        
                                        create_new_log(logger,'workflow',"inspect",'Submit application {} to AppInspect'.format(app["name"]),wkf['name'],200,"")
                                        
                                        request_id = valresponse_json['request_id']

                                        progress_inspection.append({"app":app["name"], "status" : "PROCESSING", 'request_id' :request_id , "path" : source_package})

                                
                                while len(list(filter(processing_inspection,progress_inspection))) > 0 :
                                    time.sleep(10)
                                    for request in progress_inspection :

                                        if request['status'] == "PROCESSING" :

                                            status_url = base_url + "/v1/app/validate/status/"+request["request_id"]

                                            valresponse = requests.get( status_url, verify=False, headers=headers)
                                            
                                            valresponse_json = valresponse.json()
                    
                                            status = 'FAILURE'
                                            if valresponse_json['status'] ==  "SUCCESS" :
                                                # save report 
                                                header_report = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all", "Content-Type": "text/html"}
                                                report_url = base_url + "/v1/app/report/"+request["request_id"]
                                                reportresponse = requests.request("GET", report_url, verify=False, headers=header_report)
                                                o = open(os.path.join(reports_folder,request["app"] + "_" + jobid+".html"),"w+")
                                                o.write(reportresponse.content.decode('utf-8'))

                                                if valresponse_json['info']["error"] == 0 and valresponse_json['info']["failure"] == 0 and valresponse_json['info']["manual_check"] == 0 :
                                                    status = 'SUCCESS'
                                            elif valresponse_json['status'] ==  "PROCESSING" :
                                                status = "PROCESSING"
                                            
                                            request['status'] = status
                                            
                                            if status != "PROCESSING" :
                                                if status != "SUCCESS" :
                                                    valresponse.status_code = 406
                                                    reportresponse.status_code = 406
                                                
                                                create_new_log(logger,'workflow',"inspect",'Application {} Inspected [result: {}]'.format(request["app"],status),wkf['name'],valresponse.status_code,"")
                                                time.sleep(1)
                                                create_new_log(logger,'workflow',"report",'Inspection report for Application {} Downloaded'.format(request["app"]),wkf['name'],reportresponse.status_code,"")
                                                
                            else :
                                create_new_log(logger,'workflow',"login","Generate AppInspet Token...",wkf['name'],500,"Error generating AppInspect token...")
                create_new_log(logger,'workflow',"terminated","Action execution completed",wkf['name'],200,"Action execution completed")
            elif action['content']['type'] == 'deploy' :
                create_new_log(logger,'workflow',"workflow_step","Start DEPLOY action {}".format(action['content']['title']),wkf['name'],200,"Start DEPLOY action {}".format(action['content']['title']))
                postargs = {
                    'output_mode': 'json',
                }

                if contentaction in ["takeaslice","exportall"] :
                    postargs['mode'] = 'workflow'
                    postargs['jobname'] = jobname
                    postargs['jobid']= jobid
                    postargs['action'] = contentaction
                    postargs['contents'] = json.dumps(contents)
                    postargs['splunku'] = splunku
                    postargs['splunkp']= splunkp
                    postargs['deployanyway'] = deployanyway
                    postargs['mergelocal'] = mergelocal
                    postargs['upgradeapp'] = upgradeapp

                    for stk in action['content']['stacks'].split(",") :
                        response, content = rest.simpleRequest("/servicesNS/nobody/appcontentmanager/configs/conf-stacks/"+stk+"?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False, timeout=None)
                        if response.status in [200,201,202]:
                            s = json.loads(content)['entry'][0]
                            stacktoken=None
                            for storage_password in storage_passwords.list():
                                if storage_password.name.replace(":","") == stk :
                                    stacktoken = storage_password.clear_password

                            postargs['targets'] = json.dumps([{'name': stk, 'token': stacktoken, 'experiene' : s['content']['experience']}])
                            try :
                                response, content = rest.simpleRequest("/servicesNS/-/appcontentmanager/acms_actions", sessionKey=args['session']["authtoken"], method='POST', postargs=postargs, raiseAllErrors=False, timeout=None)
                                if response.status in [200,201,202]:
                                    create_new_log(logger,'workflow',"deploy","Deploy content to {}".format(stk),wkf['name'],200,"Deploy content to {} finished successfully".format(stk))
                                else :
                                    create_new_log(logger,'workflow',"deploy","Deploy content to {}".format(stk),wkf['name'],500,"Deploy content to {} finished with errors".format(stk))
                            except :
                                create_new_log(logger,'workflow',"deploy","Deploy content to {}".format(stk),wkf['name'],500,"Deploy content to {} finished with errors (timeout)".format(stk))
                                
                elif contentaction == "buildyourapp" :
                    postargs['mode'] = 'workflow'
                    postargs['jobname'] = jobname
                    postargs['jobid']= jobid
                    postargs['action'] = contentaction
                    postargs['contents'] = json.dumps(contents)
                    postargs['splunku'] = splunku
                    postargs['splunkp']= splunkp
                    
                    for stk in action['content']['stacks'].split(",") :
                        response, content = rest.simpleRequest("/servicesNS/nobody/appcontentmanager/configs/conf-stacks/"+stk+"?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False, timeout=None)
                        if response.status in [200,201,202]:
                            s = json.loads(content)['entry'][0]
                            stacktoken=None
                            for storage_password in storage_passwords.list():
                                if storage_password.name.replace(":","") == stk :
                                    stacktoken = storage_password.clear_password

                            postargs['targets'] = json.dumps([{'name': stk, 'token': stacktoken, 'experiene' : s['content']['experience']}])
                            
                            response, content = rest.simpleRequest("/servicesNS/-/appcontentmanager/acms_actions", sessionKey=args['session']["authtoken"], method='POST', postargs=postargs, raiseAllErrors=False, timeout=None)
                            if response.status in [200,201,202]:
                                create_new_log(logger,'workflow',"deploy","Deploy content to {}".format(stk),wkf['name'],200,"Deploy content to {} finished successfully".format(stk))
                            else :
                                create_new_log(logger,'workflow',"deploy","Deploy content to {}".format(stk),wkf['name'],500,"Deploy content to {} finished with errors".format(stk))
                                
                elif contentaction == "patchmode" :
                    postargs['mode'] = 'workflow'
                    postargs['jobname'] = jobname
                    postargs['jobid']= jobid
                    postargs['action'] = contentaction
                    postargs['contents'] = json.dumps(contents)
                    postargs['confoverride'] = confoverride
                    postargs['confowner']= confowner
                    
                    
                    for stk in action['content']['stacks'].split(",") :
                        response, content = rest.simpleRequest("/servicesNS/nobody/appcontentmanager/configs/conf-stacks/"+stk+"?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False, timeout=None)
                        if response.status in [200,201,202]:
                            s = json.loads(content)['entry'][0]
                            stacktoken=None
                            for storage_password in storage_passwords.list():
                                if storage_password.name.replace(":","") == stk :
                                    stacktoken = storage_password.clear_password

                            postargs['target'] = stk
                            postargs['experience'] = s['content']['experience']
                            postargs['token'] = stacktoken
                    
                            response, content = rest.simpleRequest("/servicesNS/-/appcontentmanager/acms_actions", sessionKey=args['session']["authtoken"], method='POST', postargs=postargs, raiseAllErrors=False, timeout=None)
                            if response.status in [200,201,202]:
                                create_new_log(logger,'workflow',"deploy","Deploy content to {}".format(stk),wkf['name'],200,"Deploy content to {} finished successfully".format(stk))
                            else :
                                create_new_log(logger,'workflow',"deploy","Deploy content to {}".format(stk),wkf['name'],500,"Deploy content to {} finished with errors".format(stk))
                create_new_log(logger,'workflow',"terminated","Action execution completed",wkf['name'],200,"Action execution completed")

            elif action['content']['type'] == 'splunk' :
                create_new_log(logger,'workflow',"workflow_step","Start SPLUNK> action {}".format(action['content']['title']),wkf['name'],200,"Start SPLUNK> action {}".format(action['content']['title']))
                if len(stacks) == 0 :
                    create_new_log(logger,'workflow',"workflow_step","No action with defined stacks to restart.",wkf['name'],500,"No action in this workflow with defined stacks to be restarted.")
                else :
                    # load passwords
                    for stk in stacks :

                        acs_url = "https://admin.splunk.com/"

                        if "stg-" in stk :
                            acs_url = "https://staging.admin.splunk.com/"
                            
                        
                        if "-shw" in stk :
                            acs_url = "https://staging.admin.splunk.com/"
                            
                        
                        if ".stg" in stk :
                            acs_url = "https://staging.admin.splunk.com/"
                            
                        for storage_password in storage_passwords.list():
                            if storage_password.name.replace(":","") == stk :
                                stacktoken = storage_password.clear_password
                                headers = {
                                    'Authorization': 'Bearer '+ stacktoken,
                                    'Content-Type': 'application/json',
                                    'User-Agent': 'ACMS'
                                }
                                response = requests.post(acs_url+stk.replace(".stg","")+'/adminconfig/v2/restart-now', headers=headers)
                                if response.status_code in [200, 201, 202]:
                                    create_new_log(logger,'workflow',"restart",'Restart triggered successfully for {}'.format(stk),wkf['name'],200,'Restart triggered successfully for {}'.format(stk))
                                else :
                                    create_new_log(logger,'workflow',"restart",'Error restarting stack {}'.format(stk),wkf['name'],500,'Error restarting stack {}'.format(stk))
                create_new_log(logger,'workflow',"terminated","Action execution completed",wkf['name'],200,"Action execution completed")
                    
        resp = {}
        resp["type"] = actiontype
        resp["mode"] = "workflow"
        resp["action"] = "terminated"
        resp["step"] = "Execution workflow actions terminated for workflow {}".format(wkf['name'])
        resp["workflow"] = wkf['name']
        resp["user"] = user
        resp["jobid"] = jobid
        resp["jobname"] = jobname
        logger.info(json.dumps(resp))
            
        result = {'payload': {}, 'status': 200}
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

        #scheduled rest calls
        if params['form_parameters'] == {} :
            params['form_parameters'] = self.convert_to_dict(params.get('query', []))

        params['query_parameters'] = self.convert_to_dict(params.get('query', []))

        return params
