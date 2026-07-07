import sys
import requests
from datetime import datetime
import uuid
import splunk
import splunk.util
import splunk.clilib.cli_common
import shutil
import gzip
import tarfile
from shutil import ignore_patterns
import errno
from splunk.rest import simpleRequest

if sys.version_info >= (3, 0):
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError, URLError
    import time, os, re, json, urllib.request, urllib.parse, urllib.error, requests
    import logging, logging.handlers
    import splunk.rest as rest, splunk.Intersplunk as si
else:
    from urllib2 import urlopen, Request, HTTPError, URLError
    import sys, time, os, re, json, urllib, requests
    import logging, logging.handlers
    import splunk.rest as rest, splunk.Intersplunk as si

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


splunk_home = os.environ['SPLUNK_HOME']
LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "rad.log"

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

def die(msg):
    logger.error(msg)
    exit(msg)

def process_local_migration_for_app (deploy_id,app_label,app_name,version,package_ret,app_type,total, app_path):
    logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" message=\"Start local migration\" version="+version+ " count="+str(total))
                            
    head = {
            'Authorization': 'Bearer '+stacktoken,
	    'User-Agent': 'SCMA'
        }
    
    # Verify that the app was already installed
    rep = 0
    while True :
        response = requests.get(acs_url+stackname+'/adminconfig/v2/apps/victoria/'+app_name, headers=head, verify=False)  # nosemgrep

        if response.status_code in [200, 201]:
            if  "status" in json.loads(response.text) :
                if json.loads(response.text)["status"] == "installed" :
                    break
                else :
                    time.sleep(15)

        else :
            time.sleep(15)
        
        if rep > 10 :
            break
        rep = rep+1
        

    if os.path.isdir(os.path.join(app_path,"local")) :
        for file in os.listdir(os.path.join(app_path,"local")):
            if file.endswith(".conf"):
                local_parsed   = splunk.clilib.cli_common.readConfFile(os.path.join(app_path,"local",file))
                for key, value in local_parsed.items():
                    
                    if key == "default" :
                        continue
                    
                    data = value
                    data["name"] = key
                    
                    response = requests.post("https://"+stackname+rest_url+"servicesNS/nobody/"+app_name+"/configs/conf-"+file.replace(".conf","")+"?output_mode=json",headers=head, data=data, verify=False)  # nosemgrep

                    # the stanza was created
                    if response.status_code in [200, 201]:
                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file="+file+" stanza="+key+" value='"+json.dumps(value)+"' message=\"Migrated\" version="+version+ " count="+str(total))

                    # the stanza already exists
                    elif response.status_code in [409]:
                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file="+file+" stanza="+key+" value='"+json.dumps(value)+"' message=\"Already Exists\" version="+version+ " count="+str(total))

                    else :
                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file="+file+" stanza="+key+" value='"+json.dumps(value)+"' message=\"Error ("+str(response.status_code)+")\" version="+version+ " count="+str(total))
                    

        # Migrate local dashboards
        if os.path.isdir(os.path.join(app_path, "local", "data", "ui", "views")) :
            for file in os.listdir(os.path.join(app_path, "local", "data", "ui", "views")) :
                if file.endswith(".xml"):
                    dash = open(os.path.join(app_path, "local", "data", "ui", "views",file), 'r') 
                    content = dash.read()
                    data = { 'name' : file.replace(".xml","") , 'eai:data': content }

                    response = requests.post("https://"+stackname+rest_url+"servicesNS/nobody/"+app_name+"/data/ui/views?output_mode=json",headers=head, data=data, verify=False)  # nosemgrep

                    if response.status_code in [200, 201]:
                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file="+file+" stanza=\"N/A\" value=\"N/A\" message=\"Migrated\" version="+version+ " count="+str(total))
                    
                    if response.status_code in [409]:
                        data = { 'eai:data': content }

                        response = requests.post("https://"+stackname+rest_url+"servicesNS/nobody/"+app_name+"/data/ui/views/"+file.replace(".xml","")+"?output_mode=json",headers=head, data=data, verify=False)  # nosemgrep

                        if response.status_code in [200, 201,409]:
                            logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file="+file+" stanza=\"N/A\" value=\"N/A\" message=\"Migrated\" version="+version+ " count="+str(total))

                        else :
                            logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file="+file+" stanza=\"N/A\" value=\""+response.text+"\" message=\"Error ("+str(response.status_code)+")\" version="+version+ " count="+str(total))
                    
                    else :
                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file="+file+" stanza=\"N/A\" value=\""+response.text+"\" message=\"Error ("+str(response.status_code)+")\" version="+version+ " count="+str(total))
        
        #Migrate local nav
        if os.path.isdir(os.path.join(app_path, "local", "data", "ui", "nav")) :
            for file in os.listdir(os.path.join(app_path, "local", "data", "ui", "nav")) :
                if file.endswith(".xml"):
                    dash = open(os.path.join(app_path, "local", "data", "ui", "nav",file), 'r') 
                    content = dash.read()
                    data = { 'name' : file.replace(".xml","") , 'eai:data': content }

                    response = requests.post("https://"+stackname+rest_url+"servicesNS/nobody/"+app_name+"/data/ui/nav?output_mode=json",headers=head, data=data, verify=False)  # nosemgrep

                    if response.status_code in [200, 201]:
                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file="+file+" stanza=\"N/A\" value=\"N/A\" message=\"Migrated\" version="+version+ " count="+str(total))

                    if response.status_code in [409]:
                        data = { 'eai:data': content }

                        response = requests.post("https://"+stackname+rest_url+"servicesNS/nobody/"+app_name+"/data/ui/nav/"+file.replace(".xml","")+"?output_mode=json",headers=head, data=data, verify=False)  # nosemgrep

                        if response.status_code in [200, 201,409]:
                            logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file="+file+" stanza=\"N/A\" value=\"N/A\" message=\"Migrated\" version="+version+ " count="+str(total))
                        else :
                            logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file="+file+" stanza=\"N/A\" value=\""+response.text+"\" message=\"Error ("+str(response.status_code)+")\" version="+version+ " count="+str(total))
                    else :
                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name  +" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file="+file+" stanza=\"N/A\" value=\""+response.text+"\" message=\"Error ("+str(response.status_code)+")\" version="+version+ " count="+str(total)) 

        # update ACL
        acl_base_url = "https://"+stackname+rest_url+"servicesNS/nobody/"+app_name
        acl_path_map = { 
                            "views":"/data/ui/views",
                            "nav":"/data/ui/nav",
                            "eventtypes":"/saved/eventtypes",
                            "savedsearches":"/saved/searches",
                            "lookups":"/data/lookup-table-files",
                            "tags":"/saved/fvtags",
                            "savedsearches":"/saved/searches"
                        }

        if os.path.exists(os.path.join(app_path,"metadata","local.meta")) :
            local_acl   = splunk.clilib.cli_common.readConfFile(os.path.join(app_path,"metadata","local.meta"))
            for key, value in local_acl.items():
                if key == "default" :
                    continue
                
                # format Data/Attributes
                data = local_acl[key]
                if "version" in data :
                    del data["version"]

                if "modtime" in data :
                    del data["modtime"]
                
                if "export" in data :

                    data["sharing"] = "app"
                    if data["export"] == "system" :
                        data["sharing"] = "global"

                    del data["export"]
                
                if "access" in data :
                    perms = data["access"].replace(" ","").split("],")
                    if len(perms) > 0 :
                        if "read" in perms[0] :
                            data["perms.read"] = perms[0].replace("read","").replace(":","").replace("]","").replace("[","").split(",")
                        elif "write" in perms[0] :
                            data["perms.write"] = perms[0].replace("write","").replace(":","").replace("]","").replace("[","").split(",")

                    if len(perms) > 1 :
                        if "read" in perms[1] :
                            data["perms.read"] = perms[1].replace("read","").replace(":","").replace("]","").replace("[","").split(",")
                        elif "write" in perms[1] :
                            data["perms.write"] = perms[1].replace("write","").replace(":","").replace("]","").replace("[","").split(",")

                    del data["access"]
                
                # Migrate only admin and nobody owners
                if "owner" in data :
                    if data["owner"] not in ["admin","nobody"] :
                        data["owner"] = "nobody"


                if data :
                    if key == "" :
                        response = requests.post("https://"+stackname+rest_url+"services/apps/local/"+app_name+"/acl?output_mode=json",headers=head, data=data, verify=False)  # nosemgrep

                    elif len(key.split("/")) <= 1 :
                        # those endpoints not support owner parameter ...
                        del data["owner"]
                        response = requests.post(acl_base_url + acl_path_map[key] +"/acl?output_mode=json",headers=head, data=data, verify=False)  # nosemgrep

                    else :
                        type = key.split("/")[0]
                        if type in ["saved","data"] :
                            response = requests.post(acl_base_url +key+"/acl?output_mode=json",headers=head, data=data, verify=False)  # nosemgrep
                            
                        else :
                            response = requests.post(acl_base_url+"/configs/conf-"+key+"/acl?output_mode=json",headers=head, data=data, verify=False)  # nosemgrep
                            

                    # the stanza was created
                    if response.status_code in [200, 201]:
                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file=\"local.meta\" stanza=\""+key+"\" value='"+json.dumps(data)+"' orig_value='"+json.dumps(local_acl[key])+"' message=\"Migrated\" version="+version+ " count="+str(total))
                    else :
                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\"  status=\"PROCESSING LOCAL CONFs\" file=\"local.meta\" stanza=\""+key+"\" value='"+response.text+"' message=\"Error ("+str(response.status_code)+")\" version="+version+ " count="+str(total))
                        

        logger.info("deploy_id="+deploy_id+" global_status=Deploying label=\""+app_label+"\" name="+app_name+" package="+package_ret+" type=\""+app_type+"\" status=INSTALLED message=\"End local migration\" version="+version+ " count="+str(total))
        time.sleep(1)
    else :
        logger.info("deploy_id="+deploy_id+" global_status=Deploying label='"+app_label+"' name="+app_name+" package=N/A type='"+app_type+"' status=INSTALLED version=N/A count="+str(total)+" message=\"The local folder does not exist :"+app_path+"\"")

if __name__ == '__main__':
    #global DEBUG_MODE

    deploy_id = str(uuid.uuid4())
    logger = setup_logger()
    logger.info('starting..')

    #dbg.set_breakpoint()

    core_apps = ["search","alert_logevent","alert_webhook","data_manager","appsbrowser","introspection_generator_addon","launcher","learned","legacy","logd_input","splunk_assist","splunk_essentials_9_0","splunk_archiver","splunk_gdi","splunk_httpinput","splunk_instrumentation","splunk_ingest_actions","splunk_internal_metrics","splunk-dashboard-studio","splunk_metrics_workspace","splunk_monitoring_console","SplunkForwarder","SplunkLightForwarder","user-prefs","sample_app","python_upgrade_readiness_app","splunk-dashboard-studio","splunk_secure_gateway","journald_input","splunk_rapid_diag"]

    try:

        
        # Parse the arguments
        args = dict()
        # get checks name from args if exists
        for x, opt in enumerate(sys.argv):
            if x > 0 :
                args[opt.split("=")[0]] = opt.split("=")[1]

        acs_url = "https://admin.splunk.com/"
        rest_url = ".splunkcloud.com:8089/"
        apps = []
        if "apps" in args :
            apps = args['apps'].split(",")
        
        stackname = ""
        if "stackname" in args :
            stackname = args['stackname']
            if "stg-" in stackname :
                acs_url = "https://staging.admin.splunk.com/"
                rest_url = ".stg.splunkcloud.com:8089/"

        stacktoken = ""
        if "stacktoken" in args :
            stacktoken = args['stacktoken']
        
        appinspecttoken = ""
        if "appinspecttoken" in args :
            appinspecttoken = args['appinspecttoken']
        
        stack_experience = ""
        if "stack_experience" in args :
            stack_experience = args['stack_experience']

        splunkbasesessionid = ""
        if "splunkbasesessionid" in args :
            splunkbasesessionid = args["splunkbasesessionid"]

        local_selected_apps = ""
        if "local_selected_apps" in args :
            local_selected_apps = args["local_selected_apps"]

        apps_versions = []
        if "selected_versions" in args :
            apps_versions = args["selected_versions"].split(",")

            
        total = round(len(apps)/6)
        selected_apps = []
        selapps = []
        idx = 0
        while idx < len(apps) : 
            current = {}
            current["license_url"] = apps[idx]
            current["Application"] = apps[idx+1]
            current["uid"] = apps[idx+2]
            current["Type"] = apps[idx+3]
            current["package_path"] = apps[idx+4]
            current["app_path"] = apps[idx+5]
            selected_apps.append(current)
            selapps.append(apps[idx+1])
            idx = idx + 6
        
        locals = []
        if local_selected_apps != "" :
            locals = local_selected_apps.split(",")

        total = len(list(set(locals) | set(selapps)))

        for app in selected_apps : 

            response = None
            while True :
                
                logger.info("deploy_id="+deploy_id+" global_status=Deploying name="+app["Application"]+" type='"+app["Type"]+"' status=DEPLOYING count="+str(total))

                if stack_experience == "victoria" :
                    if app["Type"] == "Private" :
                        headers = {
                            'X-Splunk-Authorization': appinspecttoken,
                            'Authorization': 'Bearer '+stacktoken,
                            'ACS-Legal-Ack': 'Y',
                            'Content-Type': 'application/x-www-form-urlencoded',
                        }

                        with open(app["package_path"], 'rb') as f:
                            data = f.read()
                            #data = f.read().replace(b'\n', b'')
                        
                        response = requests.post(acs_url+stackname+'/adminconfig/v2/apps/victoria', headers=headers, data=data, verify=False)  # nosemgrep

                    elif app["Type"] == "Splunk Base" :

                        version=""
                        for app_version in apps_versions :
                            if app["Application"] == app_version.split("#####")[0] :
                                version = app_version.split("#####")[1]


                        data='splunkbaseID='+app["uid"]
                        if version != "" :
                            data = data + "&version=" + version

                        headers = {
                        'X-Splunkbase-Authorization': splunkbasesessionid,
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'ACS-Licensing-Ack': app["license_url"].replace("cdn.apps.splunk.com","cdn.splunkbase.splunk.com"),
                        'Authorization': 'Bearer '+stacktoken
                        }
                        
                        response = requests.post(acs_url+stackname+'/adminconfig/v2/apps/victoria?splunkbase=true', headers=headers, data=data, verify=False)  # nosemgrep


                elif stack_experience == "classic" :
                    
                    if app["Type"] != "Splunk Base" :
                        headers = {
                            'Authorization': 'Bearer '+stacktoken,
                            'ACS-Legal-Ack': 'Y',
                        }

                        files = {
                            'token': (None, appinspecttoken),
                            'package': open(app["package_path"], 'rb'),
                        }

                        response = requests.post(acs_url+stackname+'/adminconfig/v2/apps', headers=headers, files=files, verify=False)  # nosemgrep

                    elif app["Type"] == "Splunk Base" :
                        
                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label='"+app["Application"]+"' name="+app["Application"]+" package=N/A type='"+app["Type"]+"' status='NOT SUPPORTED' version=N/A count="+str(total))
                        break

                if response != None :
                    if response.status_code in [200, 202]:
                        package_ret = ""
                        if  "package" in json.loads(response.text) :
                                package_ret = json.loads(response.text)["package"]
                        
                        app_label = app["Application"]
                        if "label" in json.loads(response.text) :
                            app_label = json.loads(response.text)["label"]

                        version = "N/A"
                        if "version" in json.loads(response.text) :
                            version = json.loads(response.text)["version"]

                        # add a small delay
                        if response.status_code in [202]:
                            time.sleep(5)

                        # check if local migration is needed
                        if app["Application"] in local_selected_apps :

                            process_local_migration_for_app (deploy_id,app_label,app["Application"],version,package_ret,app["Type"],total,app["app_path"])
                            
                            '''
                            else :
                                logger.info("deploy_id="+deploy_id+" global_status=Deploying label='"+app_label+"' name="+app["Application"]+" package=N/A type='"+app["Type"]+"' status=LOCAL_ERROR version=N/A count="+str(total)+" message=\"The local folder does not exist :"+app["app_path"]+"\"")
                            '''

                        # no local migration required
                        else :
                            currStatus = "INSTALLED"
                            if "status" in json.loads(response.text) :
                                currStatus = json.loads(response.text)["status"].upper()
                                if currStatus in ["PROCESSING"]:
                                    currStatus = "INSTALLED"
                            
                            logger.info("deploy_id="+deploy_id+" global_status=Deploying label='"+json.loads(response.text)["label"]+"' name="+app["Application"]+" package="+package_ret+" type='"+app["Type"]+"'  status="+currStatus+" version="+version+ " count="+str(total))

                        
                        break
                    elif response.status_code in [409]:
                        code = ""
                        message = ""
                        if  "message" in json.loads(response.text) :
                            message = json.loads(response.text)["message"]
                        if  "code" in json.loads(response.text) :
                            code = json.loads(response.text)["code"]

                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label='"+app["Application"]+"' name="+app["Application"]+" package=N/A type='"+app["Type"]+"' status=ERROR version=N/A count="+str(total)+" code = "+code+" message=\""+message+"\"")
                        logger.error(response.text)

                        # check if local migration is needed
                        if app["Application"] in local_selected_apps :
                            process_local_migration_for_app (deploy_id,app["Application"],app["Application"],version,"",app["Type"],total,app["app_path"])

                        break

                    elif response.status_code == 424 or response.status_code == 500:
                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label='"+app["Application"]+"' name="+app["Application"]+" package=N/A type='"+app["Type"]+"' status=WAITING version=N/A count="+str(total))
                        time.sleep(15)
                    
                    else :
                        code = ""
                        message = ""
                        if  "message" in json.loads(response.text) :
                            message = json.loads(response.text)["message"]
                        if  "code" in json.loads(response.text) :
                            code = json.loads(response.text)["code"]

                        logger.info("deploy_id="+deploy_id+" global_status=Deploying label='"+app["Application"]+"' name="+app["Application"]+" package=N/A type='"+app["Type"]+"' status=ERROR version=N/A count="+str(total)+" code = "+code+" message=\""+message+"\"")
                        logger.error(response.text)
                        break

        for app in core_apps :
            if app in local_selected_apps :
                process_local_migration_for_app (deploy_id,app,app,"","","Core",total,os.path.join(os.environ['SPLUNK_HOME'],'etc','apps',app))


        logger.info("deploy_id="+deploy_id+" global_status=completed")
    except Exception as e:
        logger.error("deploy_id="+deploy_id+" global_status=Error")
