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



class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self
    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout


target = ""
jobid = ""
user = ""
action = ""
jobname = ""
mode =""

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
        resp["stack"] = target
    else :
        resp["stack"] = stack

    if mode :
        resp["mode"] = mode


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



class ACMS_Actions(PersistentServerConnectionApplication):
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
        
        acs_url = "https://admin.splunk.com/"

        # Parse the arguments
        args = self.parse_in_string(in_string)
        
        global user
        global jobid
        global jobname
        global target
        global action
        global mode

        user = args['session']['user']

        token = ""
        target = ""
        contents = {}
        action = ""
        experience =""
        splunku= ""
        splunkp=""
        deployanyway = "no"
        targets = {}
        confoverride = False
        partitionapp = ""
        deploymentTarget = []
        newappcontent = {}
        blob = {}
        mergelocal = False
        upgradeapp = False
        confowner = "nobody"
        restartstacks = False
        isscheduling = False

        acs_url = "https://admin.splunk.com/"
        rest_url = ".splunkcloud.com:8089"


        if "mode" in args['form_parameters'] :
            mode = args['form_parameters']['mode']

        if "isscheduling" in args['form_parameters'] :
            isscheduling = args['form_parameters']['isscheduling'] in ["1","true","True"]

        if "restartstacks" in args['form_parameters'] :
            restartstacks = args['form_parameters']['restartstacks'] in ["1","true","True"]

        if "confowner" in args['form_parameters'] :
            confowner = args['form_parameters']['confowner']

        if "mergelocal" in args['form_parameters'] :
            mergelocal = args['form_parameters']['mergelocal'] in ["1","true","True"]
        
        if "upgradeapp" in args['form_parameters'] :
            upgradeapp = args['form_parameters']['upgradeapp'] in ["1","true","True"]

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

        if "token" in args['form_parameters'] :
            if isscheduling :
                token = unquote(args['form_parameters']['token'])
            else :
                token = args['form_parameters']['token']
            
        
        if "action" in args['form_parameters'] :
            action = args['form_parameters']['action']
        
        if "confoverride" in args['form_parameters'] :
            confoverride = args['form_parameters']['confoverride'] in ["1","true","True"]

        if "target" in args['form_parameters'] :
            target = args['form_parameters']['target']
            if "stg-" in target :
                acs_url = "https://staging.admin.splunk.com/"
                rest_url = ".stg.splunkcloud.com:8089"
            
            if "-shw" in target :
                acs_url = "https://staging.admin.splunk.com/"
                rest_url = ".stg.splunkcloud.com:8089"
            
            if ".stg" in target :
                acs_url = "https://staging.admin.splunk.com/"
                rest_url = ".stg.splunkcloud.com:8089"
                target = target.replace(".stg","")
        
        if "targets" in args['form_parameters'] :
            if isscheduling :
                targets = json.loads(unquote(args['form_parameters']['targets']))
            else :
                targets = json.loads(args['form_parameters']['targets'])


            for target in targets :
                if "stg-" in target["name"] :
                    target["acs_url"] = "https://staging.admin.splunk.com/"
                    target["rest_url"] = ".stg.splunkcloud.com:8089"
                
                elif "-shw" in target["name"] :
                    target["acs_url"] = "https://staging.admin.splunk.com/"
                    target["rest_url"] = ".stg.splunkcloud.com:8089"
                
                elif ".stg" in target["name"] :
                    target["acs_url"] = "https://staging.admin.splunk.com/"
                    target["rest_url"] = ".stg.splunkcloud.com:8089"
                    target["name"] = target["name"].replace(".stg","")
                else :
                    target["acs_url"] = "https://admin.splunk.com/"
                    target["rest_url"] = ".splunkcloud.com:8089"


        
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
            
        if "partitionapp" in args['form_parameters'] :
            if isscheduling :
                partitionapp = unquote(args['form_parameters']['partitionapp'])
            else :
                partitionapp = args['form_parameters']['partitionapp']
        
        if "validateapp" in args['form_parameters'] :
            if isscheduling :
                validateapp = unquote(args['form_parameters']['validateapp'])
            else :
                validateapp = args['form_parameters']['validateapp']
        
        if "deployment" in args['form_parameters'] :
            if isscheduling :
                deploymentTarget = unquote(args['form_parameters']['deployment']).split(",")
            else :
                deploymentTarget = args['form_parameters']['deployment'].split(",")
            
        
        if "experience" in args['form_parameters'] :
            experience = args['form_parameters']['experience']
        
        if "deployanyway" in args['form_parameters'] :
            deployanyway = args['form_parameters']['deployanyway']
        
        if "newappcontent" in args['form_parameters'] :
            if isscheduling :
                newappcontent = json.loads(unquote(args['form_parameters']['newappcontent']))
            else :
                newappcontent = json.loads(args['form_parameters']['newappcontent'])

        if "blob" in args['form_parameters'] :
            if isscheduling :
                blob = json.loads(unquote(args['form_parameters']['blob']))
            else :
                blob = json.loads(args['form_parameters']['blob'])
        
        headers = {
                'Authorization': 'Bearer '+ token,
                'Content-Type': 'application/json',
                'User-Agent': 'ACMS'
            }

        reports_folder = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','appcontentmanager','appserver','static','reports')
        packages_folder = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','appcontentmanager','appserver','static','packages')

        if not os.path.exists(reports_folder) :
            os.mkdir(reports_folder)

        if not os.path.exists(packages_folder) :
            os.mkdir(packages_folder)

        if action == "build" :
            with tempfile.TemporaryDirectory() as tempdir:
                os.mkdir(os.path.join(tempdir,newappcontent['name']))
                os.mkdir(os.path.join(tempdir,newappcontent['name'],"default"))
                os.mkdir(os.path.join(tempdir,newappcontent['name'],"metadata"))

                # get lookups
                if len(newappcontent['content']['lookups'])> 0 :
                    os.mkdir(os.path.join(tempdir,newappcontent['name'],"lookups"))
                    for dash in newappcontent['content']['lookups'] :
                        for lookup in newappcontent['content']['lookups'] :
                            src = os.path.join(splunk_home,"etc","apps",lookup['app'],"lookups",lookup['name'])
                            dst = os.path.join(tempdir,newappcontent['name'],"lookups", lookup['name'])
                            shutil.copyfile(src, dst)

                # get dashboards
                if len(newappcontent['content']['dashboards']) > 0 :
                    os.mkdir(os.path.join(tempdir,newappcontent['name'],"default","data"))
                    os.mkdir(os.path.join(tempdir,newappcontent['name'],"default","data","ui"))
                    os.mkdir(os.path.join(tempdir,newappcontent['name'],"default","data","ui","views"))

                    headers={'authorization' : "Splunk %s" % args['session']["authtoken"]}
                    for dash in newappcontent['content']['dashboards'] :
                        response, content = rest.simpleRequest("/servicesNS/"+args['session']['user']+"/"+dash['app']+"/data/ui/views/"+dash['name']+"?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False)
                        #response = requests.get("https://localhost:8089/servicesNS/"+user+"/"+dash['app']+"/data/ui/views/"+dash['name']+"?output_mode=json",headers=headers, verify=False)
                        if response.status in [200,201,202]:
                            data = json.loads(content)['entry'][0]['content']['eai:data']
                            with open(os.path.join(tempdir,newappcontent['name'],"default","data","ui","views",dash['name']+".xml"),"w+") as d :
                                d.write(data)

                # get navs
                if len(newappcontent['content']['nav']) > 0 :
                    if not os.path.exists(os.path.join(tempdir,newappcontent['name'],"default","data")) :
                        os.mkdir(os.path.join(tempdir,newappcontent['name'],"default","data"))
                        os.mkdir(os.path.join(tempdir,newappcontent['name'],"default","data","ui"))
                    
                    os.mkdir(os.path.join(tempdir,newappcontent['name'],"default","data","ui","nav"))

                    headers={'authorization' : "Splunk %s" % args['session']["authtoken"]}
                    for nav in newappcontent['content']['nav'] :
                        response, content = rest.simpleRequest("/servicesNS/"+args['session']['user']+"/"+nav['app']+"/data/ui/nav?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False)
                        if response.status in [200,201,202]:
                            data = json.loads(content)['entry'][0]['content']['eai:data']
                            with open(os.path.join(tempdir,newappcontent['name'],"default","data","ui","nav","default.xml"),"w+") as d :
                                d.write(data)

                # generate icones
                if newappcontent['icon'] != '' :
                    os.mkdir(os.path.join(tempdir,newappcontent['name'],"static"))
                    with open(os.path.join(tempdir,newappcontent['name'],"static","appIcon_2x.png"), "wb") as fh:
                        fh.write(base64.decodebytes(bytes(newappcontent['icon'].replace("data:image/png;base64,",""),"ASCII")))
                    with open(os.path.join(tempdir,newappcontent['name'],"static","appIconAlt_2x.png"), "wb") as fh:
                        fh.write(base64.decodebytes(bytes(newappcontent['icon'].replace("data:image/png;base64,",""),"ASCII")))
                    with open(os.path.join(tempdir,newappcontent['name'],"static","appIcon.png"), "wb") as fh:
                        fh.write(base64.decodebytes(bytes(newappcontent['icon'].replace("data:image/png;base64,",""),"ASCII")))
                    with open(os.path.join(tempdir,newappcontent['name'],"static","appIconAlt.png"), "wb") as fh:
                        fh.write(base64.decodebytes(bytes(newappcontent['icon'].replace("data:image/png;base64,",""),"ASCII")))
                    

                for confFile in newappcontent['content']['default'] :
                    c = {}
                    for stanza in confFile['stanzas'] :
                        c[stanza['name']] = {}
                        for conf in stanza['confs'] :
                            c[stanza['name']][conf['key']] = conf['value']
                    
                    splunk.clilib.cli_common.writeConfFile(os.path.join(tempdir,newappcontent['name'],"default",confFile['name']+".conf"),c)

                # add a metadata default file 
                meta = {}
                meta[''] = {}
                meta['']["access"] = 'read : [ * ], write : [ admin ]'
                meta['']["export"] = 'system'
                splunk.clilib.cli_common.writeConfFile(os.path.join(tempdir,newappcontent['name'],"metadata","default.meta"),meta)

                #validate the new app
                argv = []
                argv.append(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))
                argv.append("validate")
                argv.append(os.path.join(tempdir,newappcontent['name']))
                validation_results = slimmain(argv)

                # check if there is errors 
                state = "SUCCESS"
                for st in validation_results :
                    if st['level'] == 'ERROR' :
                        state = 'ERROR'

                apppath =""
                # if success package the app to appserver/static/packages folder
                if state == "SUCCESS" :
                    argv = []
                    argv.append(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))
                    argv.append("package")

                    argv.append(os.path.join(tempdir,newappcontent['name']))
                    argv.append("-o")
                    argv.append(packages_folder)
                    results = slimmain(argv)

                    package_errors = list(filter(result_errors,results))
                    if len(package_errors) == 0 :
                        apppath = results[-1]["msg"].replace('Source package exported to  "','').replace('"','')
                    else :
                        state = "ERROR"


                return {"payload" : {'results':validation_results, 'path' : apppath, 'validation_status': state}, "status":200}


        elif action == "savevalidate" :

            with open(os.path.join(packages_folder,blob['name']), "wb") as fh:
                fh.write(base64.urlsafe_b64decode(blob['value'].replace("data:application/x-gzip;base64,","")))
            time.sleep(2)
            argv = []
            argv.append(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))
            argv.append("validate")
            argv.append(os.path.join(packages_folder,blob['name']))
            results = []
            try :
                results = slimmain(argv)
            except Exception as e:
                results.append({"level" : "ERROR", "msg" : "Application uploaded, but cannot be validated. only .spl and .tar.gz packages format are supported."})

            return {"payload" : results, "status":200}

        elif action == "validate" :
            argv = []
            argv.append(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))
            argv.append("validate")
            argv.append(os.path.join(splunk_home,"etc","apps",validateapp))
            results = slimmain(argv)
            return {"payload" : results, "status":200}
        
        elif action == "partition" :
            with tempfile.TemporaryDirectory() as tempdir:
                payload = {}
                try :
                    headers={'authorization' : "Splunk %s" % args['session']["authtoken"]}
                    response, content = rest.simpleRequest('/services/apps/local/'+partitionapp+'/package?output_mode=json', sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False)
                    #response = requests.get('https://localhost:8089/services/apps/local/'+partitionapp+'/package?output_mode=json', verify=False, headers=headers)

                    if response.status in [200,201,202]:
                        tar = tarfile.open(os.path.join(splunk_home,"share","splunk","app_packages",partitionapp+".spl"))

                        tar.extractall(tempdir)

                        #shutil.copytree(os.path.join(splunk_home,"etc","apps",partitionapp),os.path.join(tempdir,partitionapp))
                        #remove app manifest
                        if os.path.exists(os.path.join(tempdir,partitionapp,"app.manifest")):
                            os.remove(os.path.join(tempdir,partitionapp,"app.manifest"))

                        # remove local metadata file
                        if os.path.exists(os.path.join(tempdir,partitionapp,"metadata","local.meta")):
                            os.remove(os.path.join(tempdir,partitionapp,"metadata","local.meta"))

                        #package the app
                        argv = []
                        argv.append(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))
                        argv.append("package")

                        argv.append(os.path.join(tempdir,partitionapp))
                        #sys.argv.append("/Users/akouki/Documents/Splunks/9.1.1/splunk/etc/apps/splunk_app_for_nix")
                        argv.append("-o")
                        argv.append(tempdir)
                    
                    
                        results = slimmain(argv)
                        package_errors = list(filter(result_errors,results))
                        if len(package_errors) > 0 :
                            logger.info("error while packaging app")
                            payload = {"app":partitionapp, "status":"error", "packages":[], "msg": "error while packaging app"}
                        else: 
                            source_package = results[-1]["msg"].replace('Source package exported to  "','').replace('"','')
                            #partition
                            argv = []
                            argv.append(re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0]))
                            argv.append("partition")
                            argv.append(source_package)
                            argv.append("-o")
                            argv.append(packages_folder)
                            argv.append("--deployment-packages")

                            for dep in deploymentTarget :
                                if dep == "searchHead" :
                                    argv.append('{"name":"searchHead","workload":["searchHead"]}')
                                if dep == "heavyForwarder" :
                                    argv.append('{"name":"heavyForwarder","workload":["indexer", "forwarder"]}')
                                if dep == "forwarder" :
                                    argv.append('{"name":"forwarder","workload":["forwarder"]}')
                                if dep == "shidx" :
                                    argv.append('{"name":"searchHeadIndexer","workload":["searchHead","indexer"]}')
                                if dep == "indexer" :
                                    argv.append('{"name":"indexer","workload":["searchHead","indexer"]}')
                            
                            results = slimmain(argv)

                            if results[-1]["msg"].startswith("Generated deployment packages for") :
                                packages = results[-1]["msg"].split("\n")[1:]
                                for pkg in packages :
                                    with tempfile.TemporaryDirectory() as tempdir:
                                        appName = pkg.strip().split("/")[-1]
                                        pkgApp = tarfile.open(pkg.strip())
                                        pkgApp.extractall(tempdir)
                                        pkgApp.close()
                                        
                                        # read splunk generated package
                                        pkgApp = tarfile.open(os.path.join(tempdir, appName.replace(".tar.gz",""),appName))
                                        os.mkdir(os.path.join(tempdir,"temp"))
                                        pkgApp.extractall(os.path.join(tempdir,"temp"))
                                        pkgApp.close()

                                        for dir in os.listdir(os.path.join(tempdir,"temp")):
                                            d = os.path.join(os.path.join(tempdir,"temp"), dir)
                                            if os.path.isdir(d):
                                                AppConf = splunk.clilib.cli_common.readConfFile(os.path.join(d,"default","app.conf"))
                                                
                                                suffix=""
                                                if "-searchHead" in appName :
                                                    suffix = "SearchHead"
                                                elif "-heavyForwarder" in appName :
                                                    suffix = "HeavyForwarder"
                                                elif "-forwarder" in appName :
                                                    suffix = "Forwarder"
                                                elif "-indexer" in appName :
                                                    suffix = "Indexer"
                                                elif "-searchHeadIndexer" in appName :
                                                    suffix = "SearchHeadIndexer"

                                                if "install" in AppConf.keys():	
                                                    if "install_source_checksum" in AppConf["install"].keys(): 
                                                        del AppConf["install"]["install_source_checksum"]
                                                    if "install_source_local_checksum" in AppConf["install"].keys():
                                                        del AppConf["install"]["install_source_local_checksum"]
                                                
                                                if "package" in AppConf.keys():
                                                    AppConf["package"]["id"] = dir+suffix
                                                else:
                                                    AppConf["package"] = {}
                                                    AppConf["package"]["id"] = dir+suffix
                                                
                                                if "id" in AppConf.keys():
                                                    AppConf["id"]["name"] = dir+suffix
                                                else:
                                                    AppConf["id"] = {}
                                                    AppConf["id"]["name"] = dir+suffix
                                                
                                                if not "launcher" in AppConf.keys():
                                                    AppConf["launcher"] = {}
                                                    AppConf["launcher"]["version"] = "1.0.0"
                                                elif not "version" in AppConf["launcher"].keys():
                                                    AppConf["launcher"]["version"] = "1.0.0"
                                                elif AppConf["launcher"]["version"] == "":
                                                    AppConf["launcher"]["version"] = "1.0.0"
                                                
                                                splunk.clilib.cli_common.writeConfFile(os.path.join(d,"default","app.conf"),AppConf)
                                                os.rename(d,os.path.join(tempdir,"temp",dir+suffix))

                                                os.remove(pkg.strip())
                                                with tarfile.open(pkg.strip(), "w:gz") as tar:
                                                    tar.add(os.path.join(tempdir,"temp",dir+suffix), arcname=os.path.basename(os.path.join(tempdir,"temp",dir+suffix)))

                                                break


                                        


                                payload = {"app":partitionapp, "status":"success", "packages":packages, "msg": "Success partitioning app"}
                            else :
                                payload = {"app":partitionapp, "status":"error", "packages":[], "msg": "error while partitioning app"}
                except Exception as e :
                    payload = {"app":partitionapp, "status":"error", "packages":[], "msg": "error while partitioning app"}

                return {"payload" : payload , "status" : 200}


        elif action == "buildyourapp" :
            appinspectResults = []
            stacks = []
            source_package = contents
            app = {}
            app["name"] = source_package.split("/")[-1]
            app["path"] = source_package

            for target in targets :
                stacks.append(target["name"])
            
            progress_inspection = []

            #get Token from appinspect
            appinspectToken = ""
            r = requests.get('https://api.splunk.com/2.0/rest/login/splunk', verify=False,auth=(splunku, splunkp))
            
            for stack in stacks :
                logger.info(json.dumps(convertResponse_to_json(r,'login', 'Generate AppInspet Token...',stack.replace(".stg",""))))
            
            if r.status_code == 200:
                appinspectToken = r.json()["data"]["token"]
            else :
                return

            base_url = "https://appinspect.splunk.com"
            validate_url = base_url + "/v1/app/validate"

            tags = ["private_app"]

            file_handler = open(source_package, "rb")
            files = {'app_package': file_handler}
            fields = {'included_tags': tags }
            
            headers = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all"}
            valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)
            
            file_handler.close()
            valresponse_json = {}
            valresponse_json = valresponse.json()
            
            for stack in stacks :
                logger.info(json.dumps(convertResponse_to_json(valresponse,'inspect','Submit application {} to AppInspect'.format(app["name"]),stack.replace(".stg",""))))
            
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
                            for stack in stacks :
                                logger.info(json.dumps(convertResponse_to_json(valresponse,'inspect','Application {} Inspected [result: {}]'.format(request["app"],status),stack.replace(".stg",""))))
                            time.sleep(1)
                            for stack in stacks :
                                logger.info(json.dumps(convertResponse_to_json(reportresponse,'report','Inspection report for Application {} Downloaded'.format(request["app"]),stack.replace(".stg",""))))

                            appinspectResults.append({'message':  "inspected", 'status': status, "app" : request["app"], "path" : request["path"] })

            vetted_app = None
            for vetted in list(filter(vetted_apps,appinspectResults)) :
                if vetted["app"] == app["name"] :
                    vetted_app = vetted
                    break
            
            if vetted_app != None :

                for target in targets :
                    if target["experience"] == "victoria" :
                        headers = {
                            'X-Splunk-Authorization': appinspectToken,
                            'Authorization': 'Bearer '+target["token"],
                            'ACS-Legal-Ack': 'Y',
                            'Content-Type': 'application/x-www-form-urlencoded',
                        }
                        with open(vetted_app["path"], 'rb') as f:
                            data = f.read()
                        install_url = "/adminconfig/v2/apps/victoria"
                        response = requests.post(target["acs_url"]+target["name"]+install_url, headers=headers, data=data, verify=False)
                        logger.info(json.dumps(convertResponse_to_json(response,'deploy','Deploy private application {}'.format(app["name"]),target["name"])))
                        if response.status_code in [200, 202]:
                            logger.info(valresponse.text)
                    else :
                        headers = {
                            'Authorization': 'Bearer '+target["token"],
                            'ACS-Legal-Ack': 'Y',
                        }

                        file_handler = open(vetted_app["path"], "rb")
                        files = {'package': file_handler, 'token' : (None,appinspectToken)}
                        
                        install_url = "/adminconfig/v2/apps"
                        response = requests.post(target["acs_url"]+target["name"]+install_url, headers=headers, files=files, verify=False)
                        logger.info(json.dumps(convertResponse_to_json(response,'deploy','Deploy private application {}'.format(app["name"]),target["name"])))
                        if response.status_code in [200, 202]:
                            logger.info(valresponse.text)
            resp = {}
            resp["mode"] = action
            resp["action"] = "terminated"
            resp["user"] = user
            resp["jobid"] = jobid
            resp["jobname"] = jobname


            for target in targets :
                resp["step"] = "Deployment Job terminated for stack {}".format(target["name"])
                resp["stack"] = target["name"]
                logger.info(json.dumps(resp))
            
            if restartstacks :
                for target in targets :
                    response = requests.post(target["acs_url"]+target["name"]+'/adminconfig/v2/restart-now', headers=headers)
                    if response.status_code in [200, 201, 202]:
                        logger.info(json.dumps(convertResponse_to_json(response,'restart','Restart triggered successfully for {}'.format(target["name"]))))
                    else :
                        logger.info(json.dumps(convertResponse_to_json(response,'restart','Error restarting stack {}'.format(target["name"]))))


            return {'payload': {}, 'status': 200}                
        
        elif action == "exportall" :
            appinspectResults = []
            stacks = []
            for target in targets :
                stacks.append(target["name"])
            # verify that there is at least one private app
            private_apps = next((app for app in contents if app['type'] in ["private","upload"]), None)
            splunkbase_apps = next((app for app in contents if app['type'] == "splunkbase"), None)
            
            with tempfile.TemporaryDirectory() as tempdir:

                if private_apps != None :
                    progress_inspection = []

                    #get Token from appinspect
                    appinspectToken = ""
                    r = requests.get('https://api.splunk.com/2.0/rest/login/splunk', verify=False,auth=(splunku, splunkp))
                    
                    for stack in stacks :
                        time.sleep(1)
                        logger.info(json.dumps(convertResponse_to_json(r,'login', 'Generate AppInspet Token...',stack.replace(".stg",""))))
                    
                    if r.status_code == 200:
                        appinspectToken = r.json()["data"]["token"]
                    else :
                        resp = {}
                        resp["mode"] = action
                        resp["action"] = "cancelled"
                        resp["step"] = "Error while generating AppInspet Token."
                        resp["user"] = user
                        resp["jobid"] = jobid
                        resp["jobname"] = jobname

                        for stack in stacks :
                            time.sleep(1)
                            resp["stack"] = stack
                            logger.info(json.dumps(resp))

                        return {"payload" : resp, "status" : r.status_code}

                    base_url = "https://appinspect.splunk.com"
                    validate_url = base_url + "/v1/app/validate"

                    for app in contents :
                        if app["type"] == "private" :

                            if mergelocal :
                                # package the app using splunk package endpoint to merge local and default
                                headers={'authorization' : "Splunk %s" % args['session']["authtoken"]}
                                response, content = rest.simpleRequest('/services/apps/local/'+app["name"]+'/package?output_mode=json', sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False)
                                #response = requests.get('https://localhost:8089/services/apps/local/'+app["name"]+'/package?output_mode=json', verify=False, headers=headers)

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
                                    #sys.argv.append("/Users/akouki/Documents/Splunks/9.1.1/splunk/etc/apps/splunk_app_for_nix")
                                    argv.append("-o")
                                    argv.append(tempdir)
                                    
                                    results = slimmain(argv)
                                    package_errors = list(filter(result_errors,results))
                                    if len(package_errors) > 0 :
                                        for stack in stacks :
                                            logger.info(json.dumps(convertResponse_to_json({"stack":stack,"status_code" : 500, "text" : "\n".join(json.dumps(r) for r in package_errors)},'package','Package application {}'.format(app["name"]))))
                                        appinspectResults.append({'message':  json.dumps(package_errors), 'status': 'error', "app" : app["name"]})
                                    
                                    else: 
                                        for stack in stacks :
                                            logger.info(json.dumps(convertResponse_to_json({"stack":stack,"status_code" : 200, "text" : "\n".join(json.dumps(r) for r in results)},"package", "Package application {}".format(app["name"]),stack.replace(".stg",""))))
                                        source_package = results[-1]["msg"].replace('Source package exported to  "','').replace('"','')
                                        
                                        
                                        tags = ["private_app"]

                                        file_handler = open(source_package, "rb")
                                        files = {'app_package': file_handler}
                                        fields = {'included_tags': tags }
                                        
                                        headers = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all"}
                                        valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)
                                        
                                        file_handler.close()
                                        valresponse_json = {}
                                        valresponse_json = valresponse.json()
                                        
                                        for stack in stacks :
                                            logger.info(json.dumps(convertResponse_to_json(valresponse,'inspect','Submit application {} to AppInspect'.format(app["name"]),stack.replace(".stg",""))))
                                        
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
                                package_errors = list(filter(result_errors,results))
                                if len(package_errors) > 0 :
                                    for stack in stacks :
                                        logger.info(json.dumps(convertResponse_to_json({"stack":stack,"status_code" : 500, "text" : "\n".join(json.dumps(r) for r in package_errors)},'package','Package application {}'.format(app["name"]))))
                                    appinspectResults.append({'message':  "_".join(package_errors), 'status': 'error', "app" : app["name"]})
                                
                                else: 
                                    for stack in stacks :
                                        logger.info(json.dumps(convertResponse_to_json({"stack":stack,"status_code" : 200, "text" : "\n".join(json.dumps(r) for r in results)},"package", "Package application {}".format(app["name"]),stack.replace(".stg",""))))
                                    source_package = results[-1]["msg"].replace('Source package exported to  "','').replace('"','')
                                    
                                    
                                    tags = ["private_app"]

                                    file_handler = open(source_package, "rb")
                                    files = {'app_package': file_handler}
                                    fields = {'included_tags': tags }
                                    
                                    headers = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all"}
                                    valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)
                                    
                                    file_handler.close()
                                    valresponse_json = {}
                                    valresponse_json = valresponse.json()
                                    
                                    for stack in stacks :
                                        logger.info(json.dumps(convertResponse_to_json(valresponse,'inspect','Submit application {} to AppInspect'.format(app["name"]),stack.replace(".stg",""))))
                                    
                                    request_id = valresponse_json['request_id']

                                    progress_inspection.append({"app":app["name"], "status" : "PROCESSING", 'request_id' :request_id , "path" : source_package})

                        elif app["type"] == "upload" :
                            # package the app using splunk package endpoint to merge local and default
                            source_package = os.path.join(packages_folder,app["name"])
                            tags = ["private_app"]

                            file_handler = open(source_package, "rb")
                            files = {'app_package': file_handler}
                            fields = {'included_tags': tags }
                            
                            headers = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all"}
                            valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)
                            
                            file_handler.close()
                            valresponse_json = {}
                            valresponse_json = valresponse.json()
                            
                            for stack in stacks :
                                logger.info(json.dumps(convertResponse_to_json(valresponse,'inspect','Submit application {} to AppInspect'.format(app["name"]),stack.replace(".stg",""))))
                            
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
                                    for stack in stacks :
                                        logger.info(json.dumps(convertResponse_to_json(valresponse,'inspect','Application {} Inspected [result: {}]'.format(request["app"],status),stack.replace(".stg",""))))
                                    time.sleep(1)
                                    for stack in stacks :
                                        logger.info(json.dumps(convertResponse_to_json(reportresponse,'report','Inspection report for Application {} Downloaded'.format(request["app"]),stack.replace(".stg",""))))

                                    appinspectResults.append({'message':  "inspected", 'status': status, "app" : request["app"], "path" : request["path"] })
                                     


                        
                    if deployanyway == "no" and len(list(filter(contain_errors,appinspectResults))) > 0 :
                        
                        resp = {}
                        resp["mode"] = action
                        resp["action"] = "cancelled"
                        resp["step"] = "Deployment cancelled due to errors during AppInspect applications vetting."
                        resp["user"] = user
                        resp["jobid"] = jobid
                        resp["jobname"] = jobname

                        for stack in stacks :
                            time.sleep(1)
                            resp["stack"] = stack
                            logger.info(json.dumps(resp))

                        return {"payload" : appinspectResults, "status" : 404}
                
                splunkid = None
                if splunkbase_apps != None :
                    data={'username': splunku, 'password': splunkp}
                    response = requests.post('https://splunkbase.splunk.com/api/account:login', data=data)
                    
                    time.sleep(1)
                    if response.status_code in [200,201,202] :
                        for target in targets :
                            logger.info(json.dumps(convertResponse_to_json(response,"login","Login: Splunkbase session ID successfully retrieved.",target["name"])))
                    
                        splunkid = response.text.split("<id>")[1].split("</id>")[0]
                    else :
                        for target in targets :
                            logger.info(json.dumps(convertResponse_to_json(response,"login","Login: Failure to retrieve Splunkbase session ID.",target["name"])))
                
                
                for app in contents :
                    if app["type"] == "splunkbase" :
                        if splunkid != None :
                            for target in targets :
                                install_url = "/adminconfig/v2/apps"
                                if target["experience"] == "victoria" :
                                    install_url = install_url+ "/victoria"

                                headers['X-Splunkbase-Authorization'] = splunkid
                                headers['Content-Type'] = "application/x-www-form-urlencoded"
                                
                                data = {'splunkbaseID': app["uid"]}
                                if app['version'] != '' :
                                    data = {'splunkbaseID': app["uid"], 'version' : app['version']}
                                headers['ACS-Licensing-Ack'] = app["license"]

                                headers['Authorization'] =  'Bearer '+ target["token"]

                                logged = False
                                while True :
                                    response = requests.post(target["acs_url"]+target["name"]+install_url+ "?splunkbase=true", headers=headers,data=data)
                                    step = "Deploy splunkbase application {}".format(app["name"])
                                    if app['version'] != '' :
                                        step = "Deploy splunkbase application {} v{}".format(app["name"],app["version"])

                                    logger.info(json.dumps(convertResponse_to_json(response,"deploy",step,target["name"])))
                                    if response.status_code in [200,201,202] :
                                        logger.info(response.text)
                                        break
                                    elif response.status_code in [409] :
                                        # object already exists , patch
                                        if upgradeapp :
                                            #del data['splunkbaseID']
                                            response = requests.patch(target["acs_url"]+target["name"]+install_url+ "/"+app["name"]+"?splunkbase=true", headers=headers,data=data)
                                            step = "Patch splunkbase application {}".format(app["name"])
                                            if app['version'] != '' :
                                                step = "Patch splunkbase application {} v{}".format(app["name"],app["version"])
                                            logger.info(json.dumps(convertResponse_to_json(response,"deploy",step,target["name"])))
                                        break
                                    elif response.status_code in [400] :
                                        if json.loads(response.text)['code'] == '400' and "Application cannot be installed while a deployment task is still in progress." in json.loads(response.text)['message'] :
                                            # an installation operation in progress , wait and retry
                                            if not logged :
                                                step = "A deployment task is still in progress. Retry in few moments."
                                                logger.info(json.dumps(convertResponse_to_json(response,"deploy",step,target["name"])))
                                                logged = True
                                            time.sleep(20)
                                        else :
                                            break
        
                                    else :
                                        break

                    elif app["type"] in ["private","upload"]:
                        vetted_app = None
                        for vetted in list(filter(vetted_apps,appinspectResults)) :
                            if vetted["app"] == app["name"] :
                                vetted_app = vetted
                                break
                        
                        if vetted_app != None :

                            for target in targets :

                                logged = False
                                while True :
                                    if target["experience"] == "victoria" :
                                        headers = {
                                            'X-Splunk-Authorization': appinspectToken,
                                            'Authorization': 'Bearer '+target["token"],
                                            'ACS-Legal-Ack': 'Y',
                                            'Content-Type': 'application/x-www-form-urlencoded',
                                        }
                                        with open(vetted_app["path"], 'rb') as f:
                                            data = f.read()
                                        install_url = "/adminconfig/v2/apps/victoria"
                                        response = requests.post(target["acs_url"]+target["name"]+install_url, headers=headers, data=data, verify=False)
                                        logger.info(json.dumps(convertResponse_to_json(response,'deploy','Deploy private application {}'.format(app["name"]),target["name"])))
                                        if response.status_code in [200, 202]:
                                            logger.info(valresponse.text)
                                            break
                                        elif response.status_code in [409] :
                                            # object already exists , patch
                                            if upgradeapp :
                                                response = requests.patch(target["acs_url"]+target["name"]+install_url+"/"+app["name"], headers=headers, data=data, verify=False)
                                                logger.info(json.dumps(convertResponse_to_json(response,'deploy','Patch private application {}'.format(app["name"]),target["name"])))
                                            break
                                        elif response.status_code in [400] :
                                            if json.loads(response.text)['code'] == '400' and "Application cannot be installed while a deployment task is still in progress." in json.loads(response.text)['message'] :
                                                # an installation operation in progress , wait and retry
                                                if not logged :
                                                    step = "A deployment task is still in progress. Retry in few moments."
                                                    logger.info(json.dumps(convertResponse_to_json(response,"deploy",step,target["name"])))
                                                    logged = True
                                                time.sleep(20)
                                            else :
                                                break
                                        else :
                                            break
                                        

                                    else :
                                        headers = {
                                            'Authorization': 'Bearer '+target["token"],
                                            'ACS-Legal-Ack': 'Y',
                                        }

                                        file_handler = open(vetted_app["path"], "rb")
                                        files = {'package': file_handler, 'token' : (None,appinspectToken)}
                                        
                                        install_url = "/adminconfig/v2/apps"
                                        response = requests.post(target["acs_url"]+target["name"]+install_url, headers=headers, files=files, verify=False)
                                        logger.info(json.dumps(convertResponse_to_json(response,'deploy','Deploy private application {}'.format(app["name"]),target["name"])))
                                        if response.status_code in [200, 202]:
                                            logger.info(valresponse.text)
                                            break
                                        elif response.status_code in [409] :
                                            # object already exists , patch
                                            if upgradeapp :
                                                response = requests.post(target["acs_url"]+target["name"]+install_url+"/"+app["name"], headers=headers, files=files, verify=False)
                                                logger.info(json.dumps(convertResponse_to_json(response,'deploy','Patch private application {}'.format(app["name"]),target["name"])))
                                            break
                                        elif response.status_code in [400] :
                                            if json.loads(response.text)['code'] == '400' and "Application cannot be installed while a deployment task is still in progress." in json.loads(response.text)['message'] :
                                                # an installation operation in progress , wait and retry
                                                if not logged :
                                                    step = "A deployment task is still in progress. Retry in few moments."
                                                    logger.info(json.dumps(convertResponse_to_json(response,"deploy",step,target["name"])))
                                                    logged = True
                                                time.sleep(20)
                                            else :
                                                break
                                        else :
                                            break
                                    
                
                resp = {}
                resp["mode"] = action
                resp["action"] = "terminated"
                resp["user"] = user
                resp["jobid"] = jobid
                resp["jobname"] = jobname

                for target in targets :
                    resp["step"] = "Deployment Job terminated for stack {}".format(target["name"])
                    resp["stack"] = target["name"]
                    logger.info(json.dumps(resp))

                if restartstacks :
                    for target in targets :
                        response = requests.post(target["acs_url"]+target["name"]+'/adminconfig/v2/restart-now', headers=headers)
                        if response.status_code in [200, 201, 202]:
                            logger.info(json.dumps(convertResponse_to_json(response,'restart','Restart triggered successfully for {}'.format(target["name"]))))
                        else :
                            logger.info(json.dumps(convertResponse_to_json(response,'restart','Error restarting stack {}'.format(target["name"]))))
                
                return {'payload': {}, 'status': 200}
            
        elif action == "takeaslice" :
            appinspectResults = []
            stacks = []
            
            for target in targets :
                stacks.append(target["name"])

            progress_inspection = []

            #get Token from appinspect
            appinspectToken = ""
            r = requests.get('https://api.splunk.com/2.0/rest/login/splunk', verify=False,auth=(splunku, splunkp))
            
            for stack in stacks :
                logger.info(json.dumps(convertResponse_to_json(r,'login', 'Generate AppInspet Token...',stack.replace(".stg",""))))
            
            if r.status_code == 200:
                appinspectToken = r.json()["data"]["token"]
            else :
                return

            base_url = "https://appinspect.splunk.com"
            validate_url = base_url + "/v1/app/validate"

            for app in contents :
                source_package = app.strip()
                appName = os.path.split(source_package)[1]
                tags = ["private_app"]

                file_handler = open(source_package, "rb")
                files = {'app_package': file_handler}
                fields = {'included_tags': tags }
                
                headers = {"Authorization": "bearer {}".format(appinspectToken), "max-messages": "all"}
                valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)
                
                file_handler.close()
                valresponse_json = {}
                valresponse_json = valresponse.json()
                
                for stack in stacks :
                    logger.info(json.dumps(convertResponse_to_json(valresponse,'inspect','Submit application {} to AppInspect'.format(appName),stack.replace(".stg",""))))
                
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
                            for stack in stacks :
                                logger.info(json.dumps(convertResponse_to_json(valresponse,'inspect','Application {} Inspected [result: {}]'.format(request["app"],status),stack.replace(".stg",""))))
                            time.sleep(1)
                            for stack in stacks :
                                logger.info(json.dumps(convertResponse_to_json(reportresponse,'report','Inspection report for Application {} Downloaded'.format(request["app"]),stack.replace(".stg",""))))

                            appinspectResults.append({'message':  "inspected", 'status': status, "app" : request["app"], "path" : request["path"] })
                                


                
            if deployanyway == "no" and len(list(filter(contain_errors,appinspectResults))) > 0 :
                
                resp = {}
                resp["mode"] = action
                resp["action"] = "cancelled"
                resp["step"] = "Deployment cancelled due to errors during AppInspect applications vetting."
                resp["user"] = user
                resp["jobid"] = jobid
                resp["jobname"] = jobname

                for stack in stacks :
                    time.sleep(1)
                    resp["stack"] = stack
                    logger.info(json.dumps(resp))

                return {"payload" : appinspectResults, "status" : 404}
                
                
            for app in contents :

                vetted_app = None
                for vetted in list(filter(vetted_apps,appinspectResults)) :
                    if vetted["app"] == appName :
                        vetted_app = vetted
                        break
                
                if vetted_app != None :

                    for target in targets :
                        if target["experience"] == "victoria" :
                            headers = {
                                'X-Splunk-Authorization': appinspectToken,
                                'Authorization': 'Bearer '+target["token"],
                                'ACS-Legal-Ack': 'Y',
                                'Content-Type': 'application/x-www-form-urlencoded',
                            }
                            with open(vetted_app["path"], 'rb') as f:
                                data = f.read()
                            install_url = "/adminconfig/v2/apps/victoria"
                            response = requests.post(target["acs_url"]+target["name"]+install_url, headers=headers, data=data, verify=False)
                            logger.info(json.dumps(convertResponse_to_json(response,'deploy','Deploy private application {}'.format(appName),target["name"])))
                            if response.status_code in [200, 202]:
                                logger.info(valresponse.text)
                        else :
                            headers = {
                                'Authorization': 'Bearer '+target["token"],
                                'ACS-Legal-Ack': 'Y',
                            }

                            file_handler = open(vetted_app["path"], "rb")
                            files = {'package': file_handler, 'token' : (None,appinspectToken)}
                            
                            install_url = "/adminconfig/v2/apps"
                            response = requests.post(target["acs_url"]+target["name"]+install_url, headers=headers, files=files, verify=False)
                            logger.info(json.dumps(convertResponse_to_json(response,'deploy','Deploy private application {}'.format(appName),target["name"])))
                            if response.status_code in [200, 202]:
                                logger.info(valresponse.text)
            
            resp = {}
            resp["mode"] = action
            resp["action"] = "terminated"
            resp["user"] = user
            resp["jobid"] = jobid
            resp["jobname"] = jobname

            for target in targets :
                resp["step"] = "Deployment Job terminated for stack {}".format(target["name"])
                resp["stack"] = target["name"]
                logger.info(json.dumps(resp))
            
            if restartstacks :
                for target in targets :
                    response = requests.post(target["acs_url"]+target["name"]+'/adminconfig/v2/restart-now', headers=headers)
                    if response.status_code in [200, 201, 202]:
                        logger.info(json.dumps(convertResponse_to_json(response,'restart','Restart triggered successfully for {}'.format(target["name"]))))
                    else :
                        logger.info(json.dumps(convertResponse_to_json(response,'restart','Error restarting stack {}'.format(target["name"]))))

            return {'payload': {}, 'status': 200}
        
        elif action == "patchmode" :
            for content in contents.keys() :
                c = content.split("###")
                app = c[0]
                file = c[1]
                stanza = c[2]
                #user = content.split("###")[3]
                sharing = c[4]
                read = c[5]
                write = c[6]
                

                #deploy dashboards
                if file == "views" :
                    response, content = rest.simpleRequest("/servicesNS/"+args['session']['user']+"/"+app+"/data/ui/views/"+stanza+"?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False)
                    #response = requests.get("https://localhost:8089/servicesNS/"+user+"/"+dash['app']+"/data/ui/views/"+dash['name']+"?output_mode=json",headers=headers, verify=False)
                    if response.status in [200,201,202]:
                        content = json.loads(content)['entry'][0]['content']['eai:data']
                        data = { 'name' : stanza , 'eai:data': content }
                        response = requests.post("https://"+target+rest_url+"/servicesNS/"+confowner+"/"+app+"/data/ui/views?output_mode=json",headers=headers, data=data, verify=False)
                        logger.info(json.dumps(convertResponse_to_json(response,"deploy","Deploy dashboard {} to application {}".format(stanza,app),target)))
                        if response.status_code in [409] and confoverride:
                            del data["name"]
                            response = requests.post("https://"+target+rest_url+"/servicesNS/"+confowner+"/"+app+"/data/ui/views/"+stanza+"?output_mode=json",headers=headers, data=data, verify=False)
                            logger.info(json.dumps(convertResponse_to_json(response,"deploy","Override Dashboard {} content in application {}".format(stanza,app),target)))
                
                #deploy Navigation
                elif file == "nav" :
                    response, content = rest.simpleRequest("/servicesNS/"+args['session']['user']+"/"+app+"/data/ui/nav?output_mode=json&count=0", sessionKey=args['session']["authtoken"], method='GET', postargs=None, raiseAllErrors=False)
                    #response = requests.get("https://localhost:8089/servicesNS/"+user+"/"+dash['app']+"/data/ui/views/"+dash['name']+"?output_mode=json",headers=headers, verify=False)
                    if response.status in [200,201,202]:
                        content = json.loads(content)['entry'][0]['content']['eai:data']
                        data = { 'name' : "default" , 'eai:data': content }
                        response = requests.post("https://"+target+rest_url+"/servicesNS/"+confowner+"/"+app+"/data/ui/nav?output_mode=json",headers=headers, data=data, verify=False)
                        logger.info(json.dumps(convertResponse_to_json(response,"deploy","Deploy default.xml navigation to application {}".format(app),target)))
                        if response.status_code in [409] and confoverride:
                            del data["name"]
                            response = requests.post("https://"+target+rest_url+"/servicesNS/"+confowner+"/"+app+"/data/ui/nav/default?output_mode=json",headers=headers, data=data, verify=False)
                            logger.info(json.dumps(convertResponse_to_json(response,"deploy","Override default.xml nav content in application {}".format(app),target)))

                else :
                    data = contents[content]
                    data["name"] = stanza
                    response = requests.post("https://"+target+rest_url+"/servicesNS/"+confowner+"/"+app+"/configs/conf-"+file+"?output_mode=json",headers=headers, data=data, verify=False)

                    logger.info(json.dumps(convertResponse_to_json(response,"deploy","Deploy stanza [{}] in {}.conf to application {}".format(stanza,file,app),target)))

                    # the stanza was created
                    if response.status_code in [409] and confoverride:
                        del data["name"]
                        response = requests.post("https://"+target+rest_url+"/servicesNS/"+confowner+"/"+app+"/configs/conf-"+file+"/"+stanza+"?output_mode=json",headers=headers, data=data, verify=False)
                        logger.info(json.dumps(convertResponse_to_json(response,"deploy","Override stanza value [{}] in {}.conf in application {}".format(stanza,file,app),target)))
                
                if response.status_code in [200,201,202] :
                    # update acl
                    time.sleep(1.5)
                    data={}
                    data['owner']=confowner
                    data['sharing']=sharing
                    data['perms.read']=read
                    data['perms.write']=write
                    response = requests.post("https://"+target+rest_url+"/servicesNS/"+confowner+"/"+app+"/configs/conf-"+file+"/"+stanza+"/acl?output_mode=json",headers=headers, data=data, verify=False)
                    logger.info(json.dumps(convertResponse_to_json(response,"deploy","Apply ACLs (Sharing: {}, Read:[{}], Write:{}) to stanza value [{}] in {}.conf in application {}".format(sharing,read,write,stanza,file,app),target)))
            
            resp = {}
            resp["mode"] = action
            resp["action"] = "terminated"
            resp["user"] = user
            resp["jobid"] = jobid
            resp["jobname"] = jobname
            resp["stack"] = target
            resp["step"] = "Deployment Job terminated for stack {}".format(target)

            if restartstacks :
                response = requests.post(acs_url+target+'/adminconfig/v2/restart-now', headers=headers)
                if response.status_code in [200, 201, 202]:
                    logger.info(json.dumps(convertResponse_to_json(response,'restart','Restart triggered successfully for {}'.format(target),target)))
                else :
                    logger.info(json.dumps(convertResponse_to_json(response,'restart','Error restarting stack {}'.format(target),target)))

            logger.info(json.dumps(resp))
                
            return {'payload': {}, 'status': 200}
        
                    
        resp = {}
        resp["mode"] = action
        resp["action"] = "terminated"
        resp["step"] = "Deployment Job terminated for stack {}".format(target)
        resp["stack"] = target
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
