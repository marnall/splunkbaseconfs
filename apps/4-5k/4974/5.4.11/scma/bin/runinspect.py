import logging
import os
import sys
import json
import cherrypy
import splunk
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util
import splunk.util
import splunk.clilib.cli_common
import shutil
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib import jsonresponse
import urllib
import httplib2
from splunk.rest import simpleRequest
import base64
import requests
import subprocess
import shlex
import logging.handlers
import splunk.rest
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.clilib import cli_common as cli
import time
import tempfile
import uuid
import splunk.entity as entity
from subprocess import call
import splunk.entity, splunk.Intersplunk 

from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.util import normalizeBoolean
import tarfile
import os.path

import tempfile
import stat
from datetime import datetime
import splunk.clilib.cli_common
import errno
from shutil import ignore_patterns
import gzip

splunk_home = os.environ['SPLUNK_HOME']
debugmode = False

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

def setup_logger():
    logger = logging.getLogger('samrt_services')
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(
                    make_splunkhome_path(['var', 'log', 'splunk', 
                                          'automatic-applications-assessment.log']),
                                        maxBytes=25000000, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

class RunInspect(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def list_files(self, startpath):
        if debugmode :
            logger.info("[DEBUG] |== Start list_files function")
        structure = ""
        for root, dirs, files in os.walk(startpath):
            level = root.replace(startpath, '').count(os.sep)
            indent = '-' * 4 * (level)
            structure = structure + "###" + '{}{}/'.format(indent, os.path.basename(root))
            subindent = '-' * 4 * (level + 1)
            for f in files:
                structure = structure + "###" + '{}{}'.format(subindent, f)
                
        return structure

    def is_valid_app_dir(self, path):
        if debugmode :
            logger.info("[DEBUG] |== Start is_valid_app_dir function")

        for name in os.listdir(path) :
            if os.path.isdir(os.path.join(path,name)) and (name=="local" or name=="default") :
                return True
        return False

    def get_appid(self, app_archive):

        if debugmode :
            logger.info("[DEBUG] |== Start get_appid function")

        appid=""

        try:
            tar_file = app_archive
            tar = tarfile.open(tar_file, "r:gz")
            members = tar.getmembers()
            
            if len(members) > 0:
                for member in members:
                    if member.isfile() and os.path.basename(member.name) == "app.conf" :
                        f = tar.extractfile(member)
                        if f is not None:
                            for line in f.readlines() :
                                line=line.decode("utf-8").replace(" ","").replace("\n","")
                                if line.split("=")[0] == 'id':
                                    appid = line.split("=")[1]
        except Exception as e:
            logger.error("error while getting appid")

        return appid
    
    def is_splunkbase_app(self, appid):

        if debugmode :
            logger.info("[DEBUG] |== Start is_splunkbase_app function")

        if not appid or (appid == "") :
            return False

        results_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','splunkbase_apps.csv.gz')

        try :
            if os.path.exists(results_file):
                with gzip.open(results_file, 'rb') as f:
                #f=open(results_file, "r")
                    if appid in f.read().decode("utf-8") :
                        return True

        finally:
            return False

    def inspect_app(self,app_name, app_path, job_id, token, appid, timestamp,count,original_path, tags):

        if debugmode :
            logger.info("[DEBUG] |== Start inspect_app function")
            logger.info("[DEBUG] Start Inspect " + app_name + " , Path= " + app_path)

        print("------ Start Inspect : " + app_name)
        valresponse_json = {}
        structure = ""

        try:
            tar = tarfile.open(app_path,"r:gz")
            tar.extractall("/tmp")  # nosemgrep
            
            tar.close()

            #structure = self.get_structure("/tmp/"+tar.members[0].path.split("/")[0])

            structure = self.list_files("/tmp/"+tar.members[0].path.split("/")[0])
            shutil.rmtree("/tmp/"+tar.members[0].path.split("/")[0])

            included_tags = []
            included_tags.append(tags)
            #add scma tag to help appinspect team to identify source requests
            included_tags.append("scma")

            print(os.path.splitext(app_name)[0])
            base_url = "https://appinspect.splunk.com"
            validate_url = base_url + "/v1/app/validate"

            file_handler = open(app_path, "rb")
            files = {'app_package': file_handler}
            fields = {'included_tags': included_tags }
            
            headers = {"Authorization": "bearer {}".format(token), "max-messages": "all"}
            
            results_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','scma_aaa_results.csv')

            if not os.path.exists(results_file) :
                fw=open(results_file, "w")
                fw.write("job_id,request_id,status,app_name,error,failure,skipped,manual_check,not_applicable,warning,success,appid,app_path,structure,timestamp,count\n")
                fw.close()
            
            
            f=open(results_file, "a")
            
            # start validating apps
            valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)  # nosemgrep
            file_handler.close()
            valresponse_json = {}

            if debugmode :
                logger.info("[DEBUG] AppInspect API call response code : "+ str(valresponse.status_code))

            if valresponse.status_code == 200 :
                valresponse_json = valresponse.json()
                if debugmode :
                    logger.info("[DEBUG] AppInspect API call response : "+json.dumps(valresponse_json))

                new_line = job_id +","+ valresponse_json["request_id"]+","+"PROCESSING,"+os.path.splitext(app_name)[0]+",0,0,0,0,0,0,0,"+appid.replace(",",".")+","+original_path+","+structure+","+timestamp+","+str(count)
                new_line = new_line.replace("\r","").replace("\n","")
                new_line = new_line +"\r\n"
                f.write(new_line)
            else :
                new_line = job_id +",N/A,"+"FAILED,"+os.path.splitext(app_name)[0]+",0,0,0,0,0,0,0,"+appid.replace(",",".")+","+original_path+","+structure+","+timestamp+","+str(count)
                new_line = new_line.replace("\r","").replace("\n","")
                new_line = new_line +"\r\n"
                f.write(new_line)

            f.close()

            logger.info("JSON Response for app " +original_path + " :\n" + json.dumps(valresponse_json))

            # Remove _tmp directory
            #shutil.rmtree(tmp_dir)
        
        except Exception as e :

            if debugmode :
                logger.info("[DEBUG] Error Inspecting : " + app_name)
                logger.info("[DEBUG] Exception: {}".format({e}))

            else :
                logger.error("Something Bad happened: {}".format({e}))

            print("------ Error Inspecting : " + app_name)
            return
        
        print("------ Finish Inspect : " + app_name)
        if debugmode :
            logger.info("[DEBUG] Finish Inspecting : " + app_name)

        return valresponse_json
        
    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
        it will automatically be JSON encoded before being returned.
        """

        global debugmode

        # Parse the arguments
        args = self.parse_in_string(in_string)

        payload = {
            "Status": "OK"
        }

        #dbg.set_breakpoint()
        timestamp = ""

        if sys.version_info[0] == 3 :
            timestamp = str(datetime.timestamp(datetime.now()))

        if sys.version_info[0] == 2 :
            timestamp = str(time.mktime(datetime.now().timetuple()))
            
        job_id = str(uuid.uuid4())
        
        token = args['form_parameters']["token"]

        #tmp_dir = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'appinspect', 'local','_tmp')
        #file_path = os.path.join(tmp_dir, file_name)
        #file_path = "/tmp/testing_app.tgz"
        apps_count = 0


        merge = args['form_parameters']["merge"]
        deletebin = args['form_parameters']["deletebin"]
        saveapps = args['form_parameters']["saveapps"]
        packagepath = args['form_parameters']["packagepath"]
        tags = args['form_parameters']["tags"]
        debugmode = (args['form_parameters']["debugmode"].upper() == "TRUE")

        if debugmode :
            logger.info("[DEBUG] |== Start handle function")

        if "jobid" in args['form_parameters'] :
            job_id = args['form_parameters']['jobid']
            application = args['form_parameters']['application']

            if debugmode :
                logger.info("[DEBUG] Re-inspect mode, JOBID="+job_id+", Application="+application)

            results_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','scma_aaa_results.csv')
            fr=open(results_file, "r")
            lines = fr.readlines()

            fw=open(results_file, "w")
            fw.write("job_id,request_id,status,app_name,error,failure,skipped,manual_check,not_applicable,warning,success,appid,app_path,structure,timestamp,count\n")
            app_path = ""
            path = ""
            appid = "N/A"
            createTGZ = False
            timestamp = ""
            
            for line in lines :
                if (line.find(job_id) != -1 ) and (line.find(application) != -1 ) :
                    
                    # get the app path and verify that exists
                    path = line.split(',')[12].replace(".tgz","").replace("\n","")
                    appid = line.split(',')[11]
                    apps_count = int(line.split(',')[15])
                    timestamp = line.split(',')[14]
                    
                    if os.path.exists(path+".tgz") :
                        app_path = path+".tgz"
                    if os.path.exists(path+".tar.gz") :
                        app_path = path+".tar.gz"
                    elif os.path.exists(path+".spl") :
                        app_path = path+".spl"
                    elif os.path.isdir(path) :
                        splFile = self.packageApp(application,path, merge=="local",merge=="default",deletebin=="1")
                        createTGZ = True
                        app_path = splFile

                elif line.find("job_id,request_id,status,app_name,error") == -1 :
                    # delete this line
                    fw.write(line)
            
            fw.close()

            if app_path == "" :
                if debugmode :
                    logger.info("[DEBUG] Error : Application file/folder was deleted and is no more available in this path "+path)

                return {'payload': 'Error : Application file/folder was deleted and is no more available in this path: '+ path, 'status': 400}
            else :
                if debugmode :
                    logger.info("[DEBUG] Start inspecting "+application)
                self.inspect_app(application,app_path,job_id,token,appid,timestamp,apps_count,path,tags)
                if createTGZ :
                    os.remove(app_path)

                if debugmode :
                    logger.info("[DEBUG] End Re-inspecting "+application)
                return {'payload': job_id, 'status': 200}

        path = args['form_parameters']["path"]
        check_splunkbase = args['form_parameters']["check_splunkbase"]
        paths = []

        if path.startswith("#") :
            path = path[1:]
            for p in path.split("#") :
                paths.append(splunk_home + p)


        else :
            paths.append(path)
        
        if debugmode :
            logger.info("[DEBUG] Parameters : Merge="+merge+" ,deletebin="+deletebin+" ,saveapps="+saveapps+" ,packagepath="+packagepath+" ,tags="+tags+" ,check_splunkbase="+check_splunkbase+" ,Paths="+path)

        apps_count = 0
        apps_to_assess = []
        for basepath in paths :
            if not os.path.isdir(basepath):
                return {'payload': "Application's path does not exist.", 'status': 500}

            for f in os.listdir(basepath):
                isSplunkCoreApp = f in ["search","alert_logevent","alert_webhook","appsbrowser","introspection_generator_addon","launcher","learned","legacy","splunk_archiver","splunk_gdi","splunk_httpinput","splunk_instrumentation","splunk_internal_metrics","splunk_metrics_workspace","splunk_monitoring_console","SplunkForwarder","SplunkLightForwarder","user-prefs","sample_app","python_upgrade_readiness_app","splunk-dashboard-studio","splunk_secure_gateway","journald_input","splunk_rapid_diag"]
                if isSplunkCoreApp and ((check_splunkbase == "3") or (check_splunkbase == "2")):
                    appInfo = {}
                    appInfo["name"] = f
                    appInfo["id"] = f
                    appInfo["type"] = "splunkcore"
                    appInfo["path"] = os.path.join(basepath, f)
                    apps_to_assess.append(appInfo)
                    apps_count += 1
                
                elif not isSplunkCoreApp :
                    if (not f.startswith('.')) :
                        if f.endswith(".tgz")  or f.endswith(".spl") or f.endswith(".tar.gz"):
                            appid = self.get_appid(os.path.join(basepath, f))
                            is_splunkbase = self.is_splunkbase_app(appid)

                            if is_splunkbase and ((check_splunkbase == "3") or (check_splunkbase == "1")):
                                appInfo = {}
                                appInfo["name"] = f
                                appInfo["id"] = appid
                                appInfo["type"] = "splunkbase"
                                appInfo["path"] = os.path.join(basepath, f)
                                apps_to_assess.append(appInfo)
                                apps_count += 1
                            if not is_splunkbase and ((check_splunkbase == "3") or (check_splunkbase == "0")):
                                appInfo = {}
                                appInfo["name"] = f
                                appInfo["id"] = appid
                                appInfo["type"] = "private"
                                appInfo["path"] = os.path.join(basepath, f)
                                apps_to_assess.append(appInfo)
                                apps_count += 1
                        else :
                            current_path = os.path.join(basepath, f)
                            if os.path.isdir(current_path) and (not f.startswith('.')) and self.is_valid_app_dir(current_path) :
                                appid = self.getSplunkAppID(os.path.join(basepath, f,"default","app.conf"))
                                is_splunkbase = self.is_splunkbase_app(appid)

                                if is_splunkbase and ((check_splunkbase == "3") or (check_splunkbase == "1")):
                                    appInfo = {}
                                    appInfo["name"] = f
                                    appInfo["id"] = appid
                                    appInfo["type"] = "splunkbase"
                                    appInfo["path"] = os.path.join(basepath, f)
                                    apps_to_assess.append(appInfo)
                                    apps_count += 1
                                if not is_splunkbase and ((check_splunkbase == "3") or (check_splunkbase == "0")):
                                    appInfo = {}
                                    appInfo["name"] = f
                                    appInfo["id"] = appid
                                    appInfo["type"] = "private"
                                    appInfo["path"] = os.path.join(basepath, f)
                                    apps_to_assess.append(appInfo)
                                    apps_count += 1
        if debugmode :
            logger.info("[DEBUG] Applications count to assess : "+str(len(apps_to_assess)))
            logger.info("[DEBUG] Applications List : "+json.dumps(apps_to_assess))

        if len(apps_to_assess) > 500 :
            if debugmode :
                logger.info("[DEBUG] Error: limit of 500 apps submissions exceeded") 
            return {'payload': "Error: limit of 500 apps submissions exceeded.", 'status': 500}
            
        for app in apps_to_assess :
            if (app["path"].endswith(".tgz")) or (app["path"].endswith(".spl")) or (app["path"].endswith(".tar.gz")):
                
                if app["id"] in [""]:
                    self.inspect_app(app["name"],app["path"],job_id,token,"N/A",timestamp,len(apps_to_assess),app["path"],tags)
                
                else :
                    self.inspect_app(app["name"],app["path"],job_id,token,app["id"],timestamp,len(apps_to_assess),app["path"],tags)

            if os.path.isdir(app["path"]):
                
                if (app["type"] == "splunkbase") or (app["type"] == "splunkcore"):
                    splFile = self.packageApp(app["name"],app["path"],True,False,deletebin=="1")
                    self.inspect_app(app["name"],splFile,job_id,token,app["id"],timestamp,len(apps_to_assess),app["path"],tags)

                if app["type"] == "private":
                    splFile = self.packageApp(app["name"],app["path"],merge=="local",merge=="default",deletebin=="1")
                    self.inspect_app(app["name"],splFile,job_id,token,app["id"],timestamp,len(apps_to_assess),app["path"],tags)

                # manage saving generated packages
                if saveapps in ["0"]:
                    if os.path.isfile(splFile):
                        os.remove(splFile)
                
                else : 
                    
                    if os.path.isdir(packagepath):
                        outputSPL = os.path.join(packagepath,app["name"]+".spl")
                        if (app["type"] == "splunkbase") or (app["type"] == "splunkcore"):
                            outputSPL = os.path.join(packagepath,app["name"]+"_local.spl")

                        if os.path.isfile(outputSPL):
                            os.remove(outputSPL)

                        if debugmode :
                            logger.info("[DEBUG] Generated spl package was saved in this path : "+packagepath)
                        shutil.move(splFile,outputSPL)
                    else : 
                        if debugmode :
                            logger.info("[DEBUG] "+ packagepath + " is not a valid path, the generated SPL package will be deleted.")
                        logger.error(packagepath + " is not a valid path, the generated SPL package will be deleted.")
                        if os.path.isfile(splFile):
                            os.remove(splFile)

        if debugmode :
                logger.info("[DEBUG] END Inspecting JOB ID: "+job_id+" , Status: 200")
        return {'payload': job_id, 'status': 200}

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

        if debugmode :
            logger.info("[DEBUG] |== Start convert_to_dict function")

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

        if debugmode :
            logger.info("[DEBUG] |== Start parse_in_string function")

        """
        Parse the in_string
        """

        params = json.loads(in_string)

        params['method'] = params['method'].lower()

        params['form_parameters'] = self.convert_to_dict(params.get('form', []))
        params['query_parameters'] = self.convert_to_dict(params.get('query', []))

        return params


    #######
    ##
    ## this part is extract and modified from the cps-appVet.py script 
    ##
    ## __version__ = 1.6
    ## __author__ = 'Splunk CPS'
    ##
    #######

    def packageApp(self,appName, appPath, LocalOnly, IgnoreLocal,BinDelete):

        if debugmode :
            logger.info("[DEBUG] |== Start packageApp function for App: "+appName + " , Path: "+appPath)

        # Tar Up App
        splFile =  appPath + ".spl"

        if os.path.isfile(splFile):
            os.remove(splFile)

        tar = tarfile.open(splFile, "w:gz")


        self.makeTempApp(appPath,appPath+"_temp", LocalOnly, IgnoreLocal,BinDelete)
        
        # Clean garbage files
        if debugmode :
            logger.info("[DEBUG] Clean garbage files")

        for (dirpath, dirnames, filenames) in os.walk(appPath+"_temp"):
            for dirname in dirnames:
                if dirname.startswith(".") :
                    shutil.rmtree(os.path.join(dirpath,dirname))

            for file in filenames:
                # remove aliases : not supported by appinspect
                if os.path.islink(os.path.join(dirpath,file)) :
                    os.remove(os.path.join(dirpath,file))
                else :
                    os.chmod(os.path.join(dirpath,file), 0o0664)
                    if file.endswith(".pyc") or file.startswith(".") or "default.old" in dirpath or "local.meta" in file:
                        os.remove(os.path.join(dirpath,file))

        if debugmode :
            logger.info("[DEBUG] Clean app Conf (app.conf) and Meta (default.meta)")

        self.cleanAppConf(appPath+"_temp/default/app.conf",appName)
        self.cleanAppMeta(appPath+"_temp/metadata/default.meta",appPath)

        tar.add(appPath+"_temp",arcname=os.path.basename(appPath))
        tar.close()
        shutil.rmtree(appPath+"_temp")
        return(splFile)

    def mergeConf(self,originDefault,originLocal,destination):
        
        if debugmode :
            logger.info("[DEBUG] |== Start mergeConf function , originDefault="+originDefault+" ,originLocal="+originLocal+" ,destination="+destination)

        if os.path.islink(originDefault) or os.path.islink(originLocal):
            return

        if debugmode :
            logger.info("[DEBUG] Read local conf file : "+originLocal)

        local_parsed   = splunk.clilib.cli_common.readConfFile(originLocal)
        #print "%s : %s \n" % (originDefault,originLocal)
        if(os.path.isfile(originDefault)):
            if debugmode :
                logger.info("[DEBUG] Read default conf file : "+originDefault)
            default_parsed = splunk.clilib.cli_common.readConfFile(originDefault)

            merged_parsed = default_parsed
            for key, value in local_parsed.items():
                if key in default_parsed:
                    for subKey, value in local_parsed[key].items():
                        merged_parsed[key][subKey] = local_parsed[key][subKey]
                else:
                    merged_parsed[key] = value

        else:
            merged_parsed = local_parsed
        
        if debugmode :
            logger.info("[DEBUG] End Merge, Write to :"+ destination)

        splunk.clilib.cli_common.writeConfFile(destination,merged_parsed)

    def cleanAppConf(self,conf,AppName):

        if debugmode :
            logger.info("[DEBUG] |== Start cleanAppConf function , Conf file="+ conf+" ,App="+AppName)

        if os.path.islink(conf):
            return

        if debugmode :
            logger.info("[DEBUG] Read conf file "+conf)
        AppConf = splunk.clilib.cli_common.readConfFile(conf)
        
        if "install" in AppConf.keys():	
            if "install_source_checksum" in AppConf["install"].keys(): 
                del AppConf["install"]["install_source_checksum"]
            if "install_source_local_checksum" in AppConf["install"].keys():
                del AppConf["install"]["install_source_local_checksum"]

        if "package" in AppConf.keys():
            if not "id" in AppConf["package"].keys():
                AppConf["package"]["id"] = AppName
        else:
            AppConf["package"] = {}
            AppConf["package"]["id"] = AppName

        if not "ui" in AppConf.keys():
            AppConf["ui"] = {}
            AppConf["ui"]["label"] = AppName
        elif not "label" in AppConf["ui"].keys():
            AppConf["ui"]["label"] = AppName

        if not "launcher" in AppConf.keys():
            AppConf["launcher"] = {}
            AppConf["launcher"]["version"] = "1.0.0"
        elif not "version" in AppConf["launcher"].keys():
            AppConf["launcher"]["version"] = "1.0.0"
        elif AppConf["launcher"]["version"] == "":
            AppConf["launcher"]["version"] = "1.0.0"
            
        if debugmode :
            logger.info("[DEBUG] Write new confs to :"+conf)

        splunk.clilib.cli_common.writeConfFile(conf,AppConf)

    def getSplunkAppID(self,conf):

        if debugmode :
            logger.info("[DEBUG] |== Start getSplunkAppID function , conf file="+conf)

        AppConf = splunk.clilib.cli_common.readConfFile(conf)

        if "package" in AppConf.keys():
            if "id" in AppConf["package"].keys():
                return AppConf["package"]["id"]
        
        return ""

    ##############
    def cleanAppMeta(self,conf,AppName):

        if debugmode :
            logger.info("[DEBUG] |== Start cleanAppMeta function")

        if os.path.islink(conf):
            return
            
        AppConf = splunk.clilib.cli_common.readConfFile(conf)

        BadMetaKeys = [ "version", "modtime" ]
        if "app/install/install_source_checksum" in AppConf.keys():
            for k in BadMetaKeys:
                if k in AppConf["app/install/install_source_checksum"].keys():
                    del AppConf["app/install/install_source_checksum"][k]
            del AppConf["app/install/install_source_checksum"]

        splunk.clilib.cli_common.writeConfFile(conf,AppConf)

    ##############

    def makeTempApp(self,appLocation,tempLocation, LocalOnly, IgnoreLocal,BinDelete):
        
        if debugmode :
            logger.info("[DEBUG] |== Start makeTempApp function, appLocation="+appLocation+" ,tempLocation="+tempLocation)

        if os.path.isdir(tempLocation):
            shutil.rmtree(tempLocation)

        # Copy the Working App InBound
        try:
            if sys.version_info[0] == 3 :
                shutil.copytree(appLocation, tempLocation, symlinks=True, ignore_dangling_symlinks= True ,ignore=ignore_patterns('*.pyc', 'default.old*'))

            if sys.version_info[0] == 2 :
                shutil.copytree(appLocation, tempLocation, symlinks=True ,ignore=ignore_patterns('*.pyc', 'default.old*'))

        # Directories are the same
        except shutil.Error as e:
            if e.errno != errno.EEXIST:
                print('Directory not copied. Error: %s %s ' % (e,e.errno))
                raise
        # Any error saying that the directory doesn't exist
        except OSError as e:
            if e.errno != errno.EEXIST:
                print('Directory not copied. Error: %s' % e)
                raise

        # Make a MetaDirectory 
        try:
            os.mkdir(tempLocation + "/metadata")
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise  # raises the error again
        
        if LocalOnly == 1:
            # Remove the /default dir from the copy no scripts will be used		
            if(os.path.isdir(tempLocation + "/default")):
                try:
                    shutil.rmtree(tempLocation + "/default")
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise  # raises the error again

            # Remove the /appserver dir from the copy no scripts will be used		
            if(os.path.isdir(tempLocation + "/appserver")):
                try:
                    shutil.rmtree(tempLocation + "/appserver")
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise  # raises the error again

            # Remove the /static dir from the copy no scripts will be used		
            if(os.path.isdir(tempLocation + "/static")):
                try:
                    shutil.rmtree(tempLocation + "/static")
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise  # raises the error again

            # Remove the /static dir from the copy no scripts will be used		
            if(os.path.isdir(tempLocation + "/scripts")):
                try:
                    shutil.rmtree(tempLocation + "/scripts")
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise  # raises the error again
        
            if(os.path.isfile(tempLocation + "/metadata/default.meta")):
                try:
                    os.remove(tempLocation + "/metadata/default.meta")
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise  # raises the error again

            # Make a Default
            try:
                os.mkdir(tempLocation + "/default")
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise  # raises the error again

        # Move /local/data dir over
        # This directory does not support merging, so any duplicates 
        # will need to be overwritten from default

        if IgnoreLocal != 1:
            if(os.path.isdir(appLocation+"/local/data") and not os.path.isdir(tempLocation+"/default/data")):
                try:
                    if sys.version_info[0] == 3 :
                        shutil.copytree(appLocation+"/local/data",tempLocation+"/default/data",symlinks=True, ignore_dangling_symlinks= True)

                    if sys.version_info[0] == 2 :
                        shutil.copytree(appLocation+"/local/data",tempLocation+"/default/data",symlinks=True)

                # Directories are the same
                except shutil.Error as e:
                    if e.errno != errno.EEXIST:
                        print('Directory not copied. Error: %s %s ' % (e,e.errno))
                        raise
                    else:
                        print(e.errno)

                # Any error saying that the directory doesn't exist
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        print('Directory not copied. Error: %s' % e)
                        raise
                    else:
                        print(e.errno)
            else:
                for src_dir, dirs, files in os.walk(appLocation+"/local/data"):
                    dst_dir = src_dir.replace(appLocation+"/local/data", tempLocation+"/default/data", 1)
                    if not os.path.exists(dst_dir):
                        os.makedirs(dst_dir)
                    for file_ in files:
                        src_file = os.path.join(src_dir, file_)
                        dst_file = os.path.join(dst_dir, file_)
                        if os.path.exists(dst_file):
                            # in case of the src and dst are the same file
                            if os.path.samefile(src_file, dst_file):
                                continue
                            os.remove(dst_file)
                        shutil.copy(src_file, dst_dir)

        # Remove the /local dir from the copy 
        # We will use the origin app for merging to default
        try:
            shutil.rmtree(tempLocation + "/local")
            os.remove(tempLocation + "/metadata/local.meta")
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise  # raises the error again

        if BinDelete == 1:
            # Remove the /bin dir from the copy no scripts will be used		
            if(os.path.isdir(tempLocation + "/bin")):
                try:
                    shutil.rmtree(tempLocation + "/bin")
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise  # raises the error again
            # Remove the /lib dir from the copy no scripts will be used		
            if(os.path.isdir(tempLocation + "/lib")):
                try:
                    shutil.rmtree(tempLocation + "/lib")
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise  # raises the error again

        # Clean Files From Temp Directory
        for (dirpath, dirnames, filenames) in os.walk(tempLocation):
            
            if "default.old" in dirpath:
                defaultDir = dirpath.split("/")
                try:
                    shutil.rmtree(defaultDir[0] + "/" + defaultDir[1])
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise  # raises the error again

        
        if IgnoreLocal != 1:
            # Merge Files from Local 
            for (dirpath, dirnames, filenames) in os.walk(appLocation):
                for file in filenames:
                    if "local" in dirpath and ".conf" in file:
                        
                        if "inputs.conf" in file and not file.startswith("."):
                            break

                        #print "Merging local %s" % (file)
                        local_Config = os.path.join(dirpath,file)
                        
                        if LocalOnly == 1:
                            default_Config = ""
                        else:
                            default_Config = local_Config.replace("/local/","/default/",1)

                        merged_Config = tempLocation + "/default/" + file
                        
                        self.mergeConf(default_Config,local_Config,merged_Config)

                    elif "local.meta" in file and not file.startswith("."):
                        
                        #print "Merging meta %s" % (file)

                        localMeta = os.path.join(dirpath,file)
                        
                        defaultMeta = localMeta.replace("local","default")
                        merged_meta = tempLocation + "/metadata/default.meta"
                        
                        self.mergeConf(localMeta,defaultMeta,merged_meta)
