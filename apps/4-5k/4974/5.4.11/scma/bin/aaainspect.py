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

LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "aaainspect.log"


def setup_logging():  # setup logging
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

def list_files(startpath,DEBUG_MODE=False):
    if DEBUG_MODE :
        logger.debug(" |== Start list_files function")
    structure = ""
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        indent = '-' * 4 * (level)
        structure = structure + "###" + '{}{}/'.format(indent, os.path.basename(root))
        subindent = '-' * 4 * (level + 1)
        for f in files:
            structure = structure + "###" + '{}{}'.format(subindent, f)
            
    return structure

def is_valid_app_dir(path,DEBUG_MODE=False):
    if DEBUG_MODE :
        logger.debug(" |== Start is_valid_app_dir function")

    for name in os.listdir(path) :
        if os.path.isdir(os.path.join(path,name)) and (name=="local" or name=="default") :
            return True
    return False

def get_appid(app_archive,DEBUG_MODE=False):

    if DEBUG_MODE :
        logger.debug(" |== Start get_appid function")

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

def is_splunkbase_app(appid,DEBUG_MODE=False):

    if DEBUG_MODE :
        logger.debug(" |== Start is_splunkbase_app function")

    if not appid or (appid == "") :
        return False

    results_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','splunkbase_apps.csv.gz')

    try :
        if os.path.exists(results_file):
            with gzip.open(results_file, 'rb') as f:
            #f=open(results_file, "r")
                if appid in f.read().decode("utf-8") :
                    return True

    except Exception as e :
        return False

def fix_aaa_lookup():
    results_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','scma_aaa_results.csv')        
    if os.path.exists(results_file):
        f=open(results_file, "r")
        lines = f.readlines()
        if (not "job_title" in lines[0]) or (not "package_path" in lines[0]):
            lines[0] = lines[0].replace("\n","")
            newval = lines[0].split(",")

            if not "job_title" in lines[0] :
                newval.insert(1,"job_title")
                
            if not "package_path" in lines[0] :
                newval.append("package_path\n")

            lines[0]=",".join(newval)
            for idx,line in enumerate(lines) :
                if idx > 0 :
                    if len(lines[idx].split(",")) == 16 :
                        newval = lines[idx].split(",")
                        newval.insert(1,"My Job Title")
                        lines[idx]=",".join(newval)
                    
                    if len(lines[idx].split(",")) == 17 :
                        lines[idx] = lines[idx].replace("\n","")
                        newval = lines[idx].split(",")
                        newval.append("N/A\n")
                        lines[idx]=",".join(newval)
            
            fi=open(results_file, "w")
            fi.writelines(lines)
            fi.close()


def inspect_app(jobtitle, app_name, app_path, job_id, token, appid, timestamp,count,original_path, tags,DEBUG_MODE=False, outputSPL="N/A"):

    logger.info('Start inspecting application="%s" , appid="%s" , job id="%s" , job title="%s" , status="start" , total="%s"' % (app_name,appid, job_id, jobtitle, count))
    if DEBUG_MODE :
        logger.debug(" |== Start inspect_app function")
        logger.debug(" Start Inspect " + app_name + " , Path= " + app_path)

    valresponse_json = {}
    structure = ""

    try:
        tar = tarfile.open(app_path,"r:gz")
        tar.extractall("/tmp")  # nosemgrep
        
        tar.close()

        #structure = get_structure("/tmp/"+tar.members[0].path.split("/")[0])

        structure = list_files("/tmp/"+tar.members[0].path.split("/")[0])
        shutil.rmtree("/tmp/"+tar.members[0].path.split("/")[0])

        included_tags = []
        for tag in tags:
            included_tags.append(tag)

        base_url = "https://appinspect.splunk.com"
        validate_url = base_url + "/v1/app/validate"

        file_handler = open(app_path, "rb")
        files = {'app_package': file_handler}
        fields = {'included_tags': included_tags }
        
        headers = {"Authorization": "bearer {}".format(token), "max-messages": "all"}
        
        results_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','scma_aaa_results.csv')

        if not os.path.exists(results_file) :
            fw=open(results_file, "w")
            fw.write("job_id,job_title,request_id,status,app_name,error,failure,skipped,manual_check,not_applicable,warning,success,appid,app_path,structure,timestamp,count,package_path\n")
            fw.close()
        
        
        f=open(results_file, "a")
        
        # start validating apps
        valresponse = requests.request("POST", validate_url, verify=False, data=fields, files=files,headers=headers)  # nosemgrep
        file_handler.close()
        valresponse_json = {}

        if DEBUG_MODE :
            logger.debug(" AppInspect API call response code : "+ str(valresponse.status_code))

        valresponse_json = valresponse.json()
        if valresponse.status_code == 200 :
            if DEBUG_MODE :
                logger.debug(" AppInspect API call response : "+json.dumps(valresponse_json))

            new_line = job_id +","+jobtitle +","+ valresponse_json["request_id"]+","+"PROCESSING,"+os.path.splitext(app_name)[0]+",0,0,0,0,0,0,0,"+appid.replace(",",".")+","+original_path+","+structure+","+timestamp+","+str(count)+","+outputSPL
            new_line = new_line.replace("\r","").replace("\n","")
            new_line = new_line +"\r\n"
            f.write(new_line)
        else :
            new_line = job_id+"," +jobtitle +",N/A,"+"FAILED,"+os.path.splitext(app_name)[0]+",0,0,0,0,0,0,0,"+appid.replace(",",".")+","+original_path+","+structure+","+timestamp+","+str(count)+","+outputSPL
            new_line = new_line.replace("\r","").replace("\n","")
            new_line = new_line +"\r\n"
            f.write(new_line)

        f.close()
        if valresponse.status_code == 200 :
            logger.info("job id=\""+ job_id +"\"JSON Response for app " +original_path + " :\n" + json.dumps(valresponse_json))
        else :
            logger.error("job id=\""+ job_id +"\"JSON Response for app " +original_path + " :\n" + json.dumps(valresponse_json))
        # Remove _tmp directory
        #shutil.rmtree(tmp_dir)
    
    except Exception as e :

        if DEBUG_MODE :
            logger.debug(" Error Inspecting : " + app_name)
            logger.debug(" Exception: {}".format({e}))

        else :
            logger.error("Something Bad happened: {}".format({e}))

        logger.info('Error while sending application="%s" appid="%s" to appinspect. job id="%s" , job title="%s" status="error" total="%s"' % (app_name,appid, job_id,jobtitle, count))
        return
    
    if DEBUG_MODE :
        logger.debug(" Finish Inspecting : " + app_name)
    logger.info('Finish sending application="%s" appid="%s" to appinspect. job id="%s" , job title="%s" status="sent" total="%s"' % (app_name,appid, job_id,jobtitle, count))
    return valresponse_json


#######
##
## this part is extracted and modified from the cps-appVet.py script 
##
## __version__ = 1.6
## __author__ = 'Splunk CPS'
##
#######

def packageApp(appName, appPath, LocalOnly, IgnoreLocal,BinDelete,tag,DEBUG_MODE=False):

    if DEBUG_MODE :
        logger.debug(" |== Start packageApp function for App: "+appName + " , Path: "+appPath)

    # Tar Up App
    splFile =  appPath + ".spl"

    if os.path.isfile(splFile):
        os.remove(splFile)

    tar = tarfile.open(splFile, "w:gz")


    makeTempApp(appPath,appPath+"_temp", LocalOnly, IgnoreLocal,BinDelete,tag)
    
    # Clean garbage files
    if DEBUG_MODE :
        logger.debug(" Clean garbage files")

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

    if DEBUG_MODE :
        logger.debug(" Clean app Conf (app.conf) and Meta (default.meta)")

    cleanAppConf(appPath+"_temp/default/app.conf",appName,DEBUG_MODE)
    cleanAppMeta(appPath+"_temp/metadata/default.meta",appPath,DEBUG_MODE)

    tar.add(appPath+"_temp",arcname=os.path.basename(appPath))
    tar.close()
    shutil.rmtree(appPath+"_temp")
    return(splFile)

def mergeConf(originDefault,originLocal,destination,DEBUG_MODE=False):
    
    if DEBUG_MODE :
        logger.debug(" |== Start mergeConf function , originDefault="+originDefault+" ,originLocal="+originLocal+" ,destination="+destination)

    if os.path.islink(originDefault) or os.path.islink(originLocal):
        return

    if DEBUG_MODE :
        logger.debug(" Read local conf file : "+originLocal)

    local_parsed   = splunk.clilib.cli_common.readConfFile(originLocal)
    #print "%s : %s \n" % (originDefault,originLocal)
    if(os.path.isfile(originDefault)):
        if DEBUG_MODE :
            logger.debug(" Read default conf file : "+originDefault)
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
    
    if DEBUG_MODE :
        logger.debug(" End Merge, Write to :"+ destination)

    splunk.clilib.cli_common.writeConfFile(destination,merged_parsed)

def cleanAppConf(conf,AppName,DEBUG_MODE=False):

    if DEBUG_MODE :
        logger.debug(" |== Start cleanAppConf function , Conf file="+ conf+" ,App="+AppName)

    if os.path.islink(conf):
        return

    if DEBUG_MODE :
        logger.debug(" Read conf file "+conf)
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
        
    if DEBUG_MODE :
        logger.debug(" Write new confs to :"+conf)

    splunk.clilib.cli_common.writeConfFile(conf,AppConf)

def getSplunkAppID(conf,DEBUG_MODE=False):

    if DEBUG_MODE :
        logger.debug(" |== Start getSplunkAppID function , conf file="+conf)

    AppConf = splunk.clilib.cli_common.readConfFile(conf)

    if "package" in AppConf.keys():
        if "id" in AppConf["package"].keys():
            return AppConf["package"]["id"]
    
    return ""

##############
def cleanAppMeta(conf,AppName,DEBUG_MODE=False):

    if DEBUG_MODE :
        logger.debug(" |== Start cleanAppMeta function")

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

def makeTempApp(appLocation,tempLocation, LocalOnly, IgnoreLocal,BinDelete,tag,DEBUG_MODE=False):
    
    if tag == "migration_victoria" :
        if DEBUG_MODE :
            logger.debug(" |== Start makeTempApp function for tag migrate_victoria, appLocation="+appLocation+" ,tempLocation="+tempLocation)

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
                logger.error('Directory not copied. Error: %s %s ' % (e,e.errno))
                raise
        # Any error saying that the directory doesn't exist
        except OSError as e:
            if e.errno != errno.EEXIST:
                logger.error('Directory not copied. Error: %s' % e)
                raise

        # Make a MetaDirectory 
        try:
            os.mkdir(tempLocation + "/metadata")
        except OSError as e:
            if e.errno != errno.EEXIST:
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

    else :
        if DEBUG_MODE :
            logger.debug(" |== Start makeTempApp function, appLocation="+appLocation+" ,tempLocation="+tempLocation)

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
                logger.error('Directory not copied. Error: %s %s ' % (e,e.errno))
                raise
        # Any error saying that the directory doesn't exist
        except OSError as e:
            if e.errno != errno.EEXIST:
                logger.error('Directory not copied. Error: %s' % e)
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
                        logger.error('Directory not copied. Error: %s %s ' % (e,e.errno))
                        raise
                    else:
                        logger.error(e.errno)

                # Any error saying that the directory doesn't exist
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        logger.error('Directory not copied. Error: %s' % e)
                        raise
                    else:
                        logger.error(e.errno)
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
                        
                        mergeConf(default_Config,local_Config,merged_Config)

                    elif "local.meta" in file and not file.startswith("."):
                        
                        #print "Merging meta %s" % (file)

                        localMeta = os.path.join(dirpath,file)
                        
                        defaultMeta = localMeta.replace("local","default")
                        merged_meta = tempLocation + "/metadata/default.meta"
                        
                        mergeConf(localMeta,defaultMeta,merged_meta)







if __name__ == '__main__':
    #global DEBUG_MODE
    logger = setup_logging()
    logger.info('starting..')
    eStart = time.time()

    #dbg.set_breakpoint()
    
    try:

        keywords = []
        argvals = dict()

        args = dict()
        # get checks name from args if exists
        for x, opt in enumerate(sys.argv):
            if x > 0 :
                if opt.split("=")[0] == "order" :
                    if not "order" in args.keys() :
                        args["order"] = []
                    
                    args["order"].append(opt.split("=")[1])

                else :
                    args[opt.split("=")[0]] = opt.split("=")[1]

        
        results,dummy,settings = si.getOrganizedResults()
        
        check_bundle = []

        check_output = {
                        '_time': time.time(),
                    }

        #dbg.set_breakpoint()
        timestamp = ""

        if sys.version_info[0] == 3 :
            timestamp = str(datetime.timestamp(datetime.now()))

        if sys.version_info[0] == 2 :
            timestamp = str(time.mktime(datetime.now().timetuple()))
            
        job_id = str(uuid.uuid4())
        
        token = args["token"]

        apps_count = 0

        merge = "default"
        deletebin = False
        saveapps = False
        tags = ["private_classic"]
        packagepath = ""
        DEBUG_MODE = False
        check_splunkbase = "0"
        path = ""
        jobtitle = "My Job Title"
        selectedapps = ""

        if "selectedapps" in args :
            selectedapps = args["selectedapps"]

        if "merge" in args :
            merge = args["merge"]
            job_id = merge+"_"+job_id
            merge = "default"

        if "jobtitle" in args :
            jobtitle = args["jobtitle"]

        if "deletebin" in args :
            deletebin = (args["deletebin"].upper() in ["T","TRUE","1"])
        
        if "saveapps" in args :
            saveapps = (args["saveapps"].upper() in ["T","TRUE","1"])

        if "packagepath" in args :
            packagepath = args["packagepath"]

        # check if path exists
        if saveapps :
            if not os.path.isdir(packagepath):
                raise ValueError("Error : saving path does not exists")

        if "tags" in args :
            tags = args["tags"].split(",")
        
        if "debugmode" in args :
            DEBUG_MODE = (args["debugmode"].upper() in ["T","TRUE","1"])

        if "check_splunkbase" in args :
            check_splunkbase = args["check_splunkbase"]

        if "path" in args :
            path = args["path"]
        

        if DEBUG_MODE :
            logger.debug(" |== Start handle function")

        # check and fix scma_aaa_results lookup
        results_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','scma_aaa_results.csv')

        if not os.path.exists(results_file) :
            fw=open(results_file, "w")
            fw.write("job_id,job_title,request_id,status,app_name,error,failure,skipped,manual_check,not_applicable,warning,success,appid,app_path,structure,timestamp,count,package_path\n")
            fw.close()
        else :
            f=open(results_file, "r")
            lines = f.readlines()
            if (not "job_title" in lines[0]) or (not "package_path" in lines[0]):
                fix_aaa_lookup()
            f.close()


        if "jobid" in args :
            apps_count = 1
            logger.info('Start running appinspect job id="%s" , job title="%s" , status="starting" total="%s" ' % (job_id, jobtitle, str(apps_count)))
            job_id = args['jobid']
            application = ""

            if "jobid" in args :
                application = args['application']

            if DEBUG_MODE :
                logger.debug(" Re-inspect mode, JOBID="+job_id+", Application="+application)

            results_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','scma_aaa_results.csv')
            fr=open(results_file, "r")
            lines = fr.readlines()

            fw=open(results_file, "w")
            fw.write("job_id,job_title,request_id,status,app_name,error,failure,skipped,manual_check,not_applicable,warning,success,appid,app_path,structure,timestamp,count,package_path\n")
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
                        splFile = packageApp(application,path, merge=="local",merge=="default",deletebin,tags[0],DEBUG_MODE)
                        createTGZ = True
                        app_path = splFile

                elif line.find("job_id,request_id,status,app_name,error") == -1 :
                    # delete this line
                    fw.write(line)
            
            fw.close()

            if app_path == "" :
                if DEBUG_MODE :
                    logger.debug(" Error : Application file/folder was deleted and is no more available in this path "+path)
                
                raise ValueError("Error : Application file/folder was deleted and is no more available in this path "+path)

            else :
                if DEBUG_MODE :
                    logger.debug(" Start inspecting "+application)
                inspect_app(jobtitle, application,app_path,job_id,token,appid,timestamp,apps_count,path,tags,DEBUG_MODE,"N/A")
                if createTGZ :
                    os.remove(app_path)

                if DEBUG_MODE :
                    logger.debug(" End Re-inspecting "+application)
                
                check_output["job_id"] = job_id
                check_output["status"] = "Sent to appinspect"
                check_output["app_count"] = "1"
                check_bundle.append(check_output)
                si.outputResults(check_bundle) 
                exit(0)

        else :
            
            paths = []

            if path.startswith(",") :
                path = path[1:]
                for p in path.split(",") :
                    paths.append(os.environ['SPLUNK_HOME'] + p)
            else :
                paths.append(path)
            
            if DEBUG_MODE :
                logger.debug(" Parameters : Merge="+str(merge)+" ,deletebin="+str(deletebin)+" ,saveapps="+str(saveapps)+" ,packagepath="+str(packagepath)+" ,tags="+str(tags)+" ,check_splunkbase="+str(check_splunkbase)+" ,Paths="+str(path))

            
            apps_count = 0
            apps_to_assess = []
            for basepath in paths :
                if not os.path.isdir(basepath):
                    logger.error("Application's path does not exist.")

                for f in os.listdir(basepath):
                    if len(selectedapps) > 0 :
                        if not f in selectedapps :
                            continue

                    isSplunkCoreApp = f in ["search","alert_logevent","alert_webhook","data_manager","appsbrowser","introspection_generator_addon","launcher","learned","legacy","logd_input","splunk_assist","splunk_essentials_9_0","splunk_archiver","splunk_gdi","splunk_httpinput","splunk_instrumentation","splunk_ingest_actions","splunk_internal_metrics","splunk-dashboard-studio","splunk_metrics_workspace","splunk_monitoring_console","SplunkForwarder","SplunkLightForwarder","user-prefs","sample_app","python_upgrade_readiness_app","splunk-dashboard-studio","splunk_secure_gateway","journald_input","splunk_rapid_diag"]

                    if isSplunkCoreApp and ((check_splunkbase == "3") or (check_splunkbase == "2")):
                        if(os.path.exists(os.path.join(basepath, f,"local"))) :
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
                                appid = get_appid(os.path.join(basepath, f),DEBUG_MODE)
                                is_splunkbase = is_splunkbase_app(appid,DEBUG_MODE)

                                if is_splunkbase and ((check_splunkbase == "3") or (check_splunkbase == "1")):
                                    tar = tarfile.open(os.path.join(basepath, f),"r")
                                    local_app_path = f+"/local" 
                                    if local_app_path in tar.getnames() :
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
                                if os.path.isdir(current_path) and (not f.startswith('.')) and is_valid_app_dir(current_path) :
                                    appid = getSplunkAppID(os.path.join(basepath, f,"default","app.conf"),DEBUG_MODE)
                                    is_splunkbase = is_splunkbase_app(appid,DEBUG_MODE)

                                    if is_splunkbase and ((check_splunkbase == "3") or (check_splunkbase == "1")):
                                        if(os.path.exists(os.path.join(basepath, f,"local"))) :
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
            
            logger.info('Start running appinspect job id="%s" , job title="%s" status="starting" total="%s" ' % (job_id, jobtitle, str(len(apps_to_assess))))

            if DEBUG_MODE :
                logger.debug(" Applications count to assess : "+str(len(apps_to_assess)))
                logger.debug(" Applications List : "+json.dumps(apps_to_assess))

            if len(apps_to_assess) > 500 :
                if DEBUG_MODE :
                    logger.debug(" Error: limit of 500 apps submissions exceeded") 
                raise ValueError("Error: limit of 500 apps submissions exceeded.")
                
            for app in apps_to_assess :
                if (app["path"].endswith(".tgz")) or (app["path"].endswith(".spl")) or (app["path"].endswith(".tar.gz")):
                    
                    if app["id"] in [""]:
                        inspect_app(jobtitle, app["name"],app["path"],job_id,token,"N/A",timestamp,len(apps_to_assess),app["path"],tags,DEBUG_MODE,"N/A")
                    
                    else :
                        inspect_app(jobtitle, app["name"],app["path"],job_id,token,app["id"],timestamp,len(apps_to_assess),app["path"],tags,DEBUG_MODE,"N/A")

                if os.path.isdir(app["path"]):
                    
                    if (app["type"] == "splunkbase") or (app["type"] == "splunkcore"):
                        splFile = packageApp(app["name"],app["path"],True,False,deletebin,tags[0],DEBUG_MODE)
                        inspect_app(jobtitle, app["name"],splFile,job_id,token,app["id"],timestamp,len(apps_to_assess),app["path"],tags,DEBUG_MODE,"N/A")

                    if app["type"] == "private":
                        outputSPL = os.path.join(packagepath,app["name"]+".spl")
                        splFile = packageApp(app["name"],app["path"],merge=="local",merge=="default",deletebin,tags[0],DEBUG_MODE)
                        inspect_app(jobtitle, app["name"],splFile,job_id,token,app["id"],timestamp,len(apps_to_assess),app["path"],tags,DEBUG_MODE,outputSPL)

                    # manage saving generated packages
                    if not saveapps :
                        if os.path.isfile(splFile):
                            os.remove(splFile)
                    
                    else : 
                        
                        if os.path.isdir(packagepath):
                            outputSPL = os.path.join(packagepath,app["name"]+".spl")
                            if (app["type"] == "splunkbase") or (app["type"] == "splunkcore"):
                                outputSPL = os.path.join(packagepath,app["name"]+"_local.spl")

                            if os.path.isfile(outputSPL):
                                os.remove(outputSPL)

                            if DEBUG_MODE :
                                logger.debug(" Generated spl package was saved in this path : "+packagepath)
                            shutil.move(splFile,outputSPL)
                        else : 
                            if DEBUG_MODE :
                                logger.debug(" "+ packagepath + " is not a valid path, the generated SPL package will be deleted.")
                            logger.error(packagepath + " is not a valid path, the generated SPL package will be deleted.")
                            if os.path.isfile(splFile):
                                os.remove(splFile)

            if DEBUG_MODE :
                    logger.debug(" END Inspecting JOB ID: "+job_id+" , Status: 200")
            
            logger.info('Finish running appinspect job id="%s" , job title="%s" , status="success" total="%s" ' % (job_id, jobtitle, str(len(apps_to_assess))))
        
            check_output["job_id"] = job_id
            check_output["status"] = "Sent to appinspect"
            check_output["app_count"] = str(len(apps_to_assess))
            check_bundle.append(check_output)
            si.outputResults(check_bundle) 
    except Exception as e:
        logger.error('error while processing id="%s" status="error" , exception="%s"' % (job_id,e))
        si.generateErrorResults(e)
        raise Exception(e)
    finally:
        logger.info('exiting job id="%s" job title="%s", execution duration=%s seconds' % (job_id,jobtitle, time.time() - eStart))