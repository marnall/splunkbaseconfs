# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import os,platform,time
import subprocess
import sys
import csv
import re
import json
import splunk.Intersplunk as si
import saUtils
import shutil
import saDbUtils
import splunk.rest
import logging as logger
from io import open
from splunk.clilib import cli_common as cli

logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

mongo_host = ''
mongo_port = ''
mongo_db = ''
mongo_auth_db = ''
mongo_config = ''
mongo_user = ''
mongo_password = ''
mongo_dbpath = ''
splunkHome = ''
mongo_binary = ''
mongod_binary = ''
error_msg = ''
ldpath = ''
ldpath_mongo = ''
ldpath_mongod = ''
# used in both windows and Unix to redirect output and run in background for Unix.
redirect_output = '>/dev/null 2>&1 &'
# Set when running in windows as must use different syntax to start process in background.
cmdPrefix = ''
settings = ''
m_version= ''

def set_environment ():
    global mongo_host
    global mongo_port
    global mongo_db
    global mongo_auth_db
    global mongo_ssl
    global mongo_user
    global mongo_password
    global mongo_dbpath
    global mongo_config
    global splunkHome
    global running_with_auth
    global ldpath 
    global ldpath_mongo 
    global ldpath_mongod 
    global ldpath_splunk_bin
    global mongo_binary 
    global mongod_binary 
    global error_msg 
    global redirect_output
    global cmdPrefix
    global settings
    global m_version

    try:

        splunkHome=os.environ.get('SPLUNK_HOME')
        mongo_dbpath = os.path.normpath (mongo_dbpath.replace("$(SPLUNK_HOME)",splunkHome))

        # Retrieve mongo_user's password from splunk storage
        passwdEndpoint = "/services/storage/passwords/" + mongo_user + "?output_mode=json"
        settings = saUtils.getSettings(sys.stdin)
        passwdResponse, passwdContent = splunk.rest.simpleRequest (passwdEndpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
        tmp = json.loads(passwdContent)
        mongo_password = tmp['entry'][0]['content']['clear_password']

        # Splunk Version determines which version of Mongo
        serverEndpoint = "/services/server/info?output_mode=json"
        serverResponse, serverContent = splunk.rest.simpleRequest (serverEndpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
        tmp = json.loads(serverContent)
        version = tmp['entry'][0]['content']['version']
        logger.info ("xmSetupDataStore - Splunk Version: " + version)
        versionList = version.split(".")
        m_version = versionList[0];
        logger.info ("xmSetupDataStore - Is Splunk Version >= " + versionList[0])

        # Set ldpath for mongo and mongod
        ldpath_mongo = os.path.normpath (splunkHome + '/etc/apps/bv_xr/lib')
        ldpath_mongod = os.path.normpath ('"' + splunkHome + '/lib"')
        ldpath_splunk_bin = os.path.normpath ('"' + splunkHome + '/bin"')

        logger.info ("xmSetupDataStore - ldpath_mongo: [" + ldpath_mongo + "]")
        logger.info ("xmSetupDataStore - ldpath_mongod: [" + ldpath_mongod + "]")
        logger.info ("xmSetupDataStore - ldpath_splunk_bin: [" + ldpath_splunk_bin + "]")

        if (platform.system() == 'Darwin'):
            if os.getenv('DYLD_LIBRARY_PATH')  == None:
                os.environ["DYLD_LIBRARY_PATH"] = os.pathsep +  ldpath_mongo
            else:
                os.environ["DYLD_LIBRARY_PATH"] += os.pathsep +  ldpath_mongo
        elif (platform.system() == 'Windows'):
            if os.getenv('LD_LIBRARY_PATH')  == None:
                os.environ["LD_LIBRARY_PATH"] =  os.pathsep + ldpath_mongo
            else:
                os.environ["LD_LIBRARY_PATH"] +=  os.pathsep + ldpath_mongo
        else:
            if os.getenv('LD_LIBRARY_PATH')  == None:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
            else:
                os.environ["LD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo

        # Windows
        saUtils.addToPath (ldpath_mongo)
        saUtils.addToPath (ldpath_mongod)
        saUtils.addToPath (ldpath_splunk_bin)

        # Set mongod binary (daemon)
        mongod_binary = os.path.normpath (splunkHome + '/bin/mongod')
        if (platform.system() == 'Windows'):
            mongod_binary = mongod_binary + ".exe"
            redirect_output = "> NUL 2>&1"
            cmdPrefix = 'START /B '

        if not os.path.isfile(mongod_binary):
            raise Exception("xmSetupDataStore-F-000: Can't find binary file " + mongod_binary)

        # Set mongo binary (client)
        if int(m_version) >= 9:
            mongo_binary = os.path.normpath ('./' +  platform.system() + '/' + platform.architecture()[0] + '/mongo4')
        else:
            mongo_binary = os.path.normpath ('./' +  platform.system() + '/' + platform.architecture()[0] + '/mongo')

        if (platform.system() == 'Windows'):
            mongo_binary = mongo_binary + ".exe"

        logger.info ("xmSetupDataStore - mongod_binary: [" + mongod_binary + "]")
        logger.info ("xmSetupDataStore - mongo_binary: [" + mongo_binary + "]")
        logger.info ("xmSetupDataStore - redirect Output: [" + redirect_output + "]")

        if not os.path.isfile(mongo_binary):
            raise Exception("xmSetupDataStore-F-000: Can't find binary file " + mongo_binary)

        if not os.path.exists(mongo_dbpath):
            #logger.info ("mongo_dbpath: [" + mongo_dbpath + "] does not exist, creating!")
            os.makedirs(mongo_dbpath)

        return "SUCCESS"
    except Exception as e:
        pass
        error_msg = "%s" % e
        return "FAIL"

def is_mongo_running_with_auth ():

    try:
        logger.info("xmSetupDataStore - is_mongo_running_with_auth() entry")

        if (platform.system() == 'Darwin'):
            if os.getenv('DYLD_LIBRARY_PATH')  == None:
                os.environ['DYLD_LIBRARY_PATH'] = os.pathsep + ldpath_mongo
            else:
                os.environ['DYLD_LIBRARY_PATH'] += os.pathsep + ldpath_mongo
        else:
            if os.getenv('LD_LIBRARY_PATH') == None:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
            else:
                os.environ["LD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo

        cmd = mongo_binary + ' -u ' + mongo_user + ' -p ' + mongo_password + ' -authenticationDatabase ' + mongo_auth_db + ' --quiet --host 127.0.0.1 --port ' + mongo_port + ' --eval "db.runCommand({ping:1})"'
        if (platform.system() == 'Darwin'):
            cmd = "export DYLD_LIBRARY_PATH=\""+ldpath_mongo+"\"; " + cmd
        logger.info("xmSetupDataStore - CHECK MONGOD (WITH AUTH)")
        mongo_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)

        logger.info("xmSetupDataStore - MONGOD is running with auth ...")
        return "SUCCESS"

    except Exception as e:
        pass
        error_msg = "%s" % e
        logger.info("xmSetupDataStore - MONGOD is NOT running (with auth) ...")
        return "FAIL"

def is_mongo_running_with_no_auth ():
    try:
        #logger.info("xmSetupDataStore - is_mongo_running_with_no_auth() entry")

        if (platform.system() == 'Darwin'):
            if os.getenv('DYLD_LIBRARY_PATH')  == None:
                os.environ["DYLD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
            else:
                os.environ["DYLD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo
        else:
            if os.getenv('LD_LIBRARY_PATH')  == None:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
            else:
                os.environ["LD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo

        cmd = mongo_binary + ' --quiet --host 127.0.0.1 --port ' + mongo_port + ' --eval "db.runCommand({ping:1})"'
        if (platform.system() == 'Darwin'):
            cmd = "export DYLD_LIBRARY_PATH=\""+ldpath_mongo+"\"; " + cmd
        mongo_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)

        logger.info("xmSetupDataStore - DATA STORE IS RUNNING")

        logger.info("xmSetupDataStore - MONGOD is running with no auth ...")
        return "SUCCESS"

    except Exception as e:
        pass
        error_msg = "%s" % e
        logger.info("xmSetupDataStore - MONGOD is NOT running (with no auth) ...")
        return "FAIL"

def start_mongod (useAuth):
    try:
        #logger.info("xmSetupDataStore - start_mongod("+useAuth+") entry")

        if (platform.system() == 'Darwin'):
            if os.getenv('DYLD_LIBRARY_PATH')  == None:
                os.environ["DYLD_LIBRARY_PATH"] = os.pathsep + ldpath_mongod
            else:
                os.environ["DYLD_LIBRARY_PATH"] += os.pathsep + ldpath_mongod
        else:
            if os.getenv('LD_LIBRARY_PATH')  == None:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep + ldpath_mongod
            else:
                os.environ["LD_LIBRARY_PATH"] += os.pathsep + ldpath_mongod

        cmdArray = []
        if useAuth == "TRUE":
            cmd = cmdPrefix + mongod_binary + ' --bind_ip 0.0.0.0 --auth --quiet --port ' + mongo_port + ' --dbpath "' + mongo_dbpath  + '" ' + redirect_output
        else:
            cmd = cmdPrefix + mongod_binary + ' --bind_ip 0.0.0.0 --quiet --port ' + mongo_port + ' --dbpath "' + mongo_dbpath  + '" ' + redirect_output

        logger.info("xmSetupDataStore - starting MONGOD...")

        pid = subprocess.Popen(cmd,shell=True).pid

        time.sleep(10.0)

        counter = 0
        status = "FAIL"
        while counter < 10 and status != "SUCCESS":
            time.sleep(10.0)
            if useAuth == "TRUE":
                status = is_mongo_running_with_auth()
               
            else:
                status = is_mongo_running_with_no_auth()
            counter = counter + 1


        logger.info("xmSetupDataStore - Started MONGOD ...")
        return "SUCCESS"
    except Exception as e:
        pass
        error_msg = "%s" % e
        logger.info("xmSetupDataStore - Failure starting MONGOD ...")
        return "FAIL"


def create_user ():
   
    try:
        if (platform.system() == 'Darwin'):
            if os.getenv('DYLD_LIBRARY_PATH')  == None:
                os.environ["DYLD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
            else:
                os.environ["DYLD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo
        else:
            if os.getenv('LD_LIBRARY_PATH')  == None:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
            else:
                os.environ["LD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo

        cmd = mongo_binary + " " + mongo_auth_db + " --quiet --host 127.0.0.1 --port " + mongo_port + " --eval \"db.createUser( { user: '" + mongo_user + "', pwd: '" + mongo_password + "', roles: [ { role: 'root', db: 'admin' }, { role: 'userAdminAnyDatabase', db: 'admin' }, { role: 'dbAdminAnyDatabase', db: 'admin' }, { role: 'readWriteAnyDatabase', db: 'admin' } ] })\""

        if (platform.system() == 'Darwin'):
            cmd = "export DYLD_LIBRARY_PATH=\""+ldpath_mongo+"\"; "+ cmd

        logger.info("xmSetupDataStore - CREATE USER")
        mongo_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        logger.info("xmSetupDataStore - created user successfully...")
        return "SUCCESS"

    except Exception as e:
        pass
        if "already exists" in str(e.output):
            logger.info("xmSetupDataStore - user already exists ...")
            return "ALREADY_EXISTS"

        error_msg = "%s" % e
        logger.info("error_msg="+error_msg)
        logger.info("xmSetupDataStore - failure creating user ...")
        return "FAIL"

def stop_mongod (useAuth):

    try:
        #logger.info("xmSetupDataStore - stop_mongod() entry")

        if (platform.system() == 'Darwin'):
            if os.getenv('DYLD_LIBRARY_PATH')  == None:
                os.environ["DYLD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
            else:
                os.environ["DYLD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo
        else:
            if os.getenv('LD_LIBRARY_PATH')  == None:
                os.environ["LD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
            else:
                os.environ["LD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo

        cmd = ''
        if useAuth == "TRUE":
            cmd = mongo_binary + ' ' + mongo_auth_db + ' -u ' + mongo_user + ' -p ' + mongo_password + ' -authenticationDatabase ' + mongo_auth_db + ' --quiet --host 127.0.0.1 --port ' + mongo_port + ' --eval "db.shutdownServer()"'
        else:
            cmd = mongo_binary + ' ' + mongo_auth_db + ' --quiet --host 127.0.0.1 --port ' + mongo_port + ' --eval "db.shutdownServer()"'
        if (platform.system() == 'Darwin'):
            cmd = "export DYLD_LIBRARY_PATH="+ldpath_mongo+"; " + cmd

        mongo_output = subprocess.check_output(cmd, shell=True)
        #logger.info("xmSetupDataStore - STOP MONGO RESULT: " + mongo_output)
        #logger.info("xmSetupDataStore - MONGOD STOPPED")
        time.sleep(10.0)

        logger.info("xmSetupDataStore - MONGOD stopped successfully...")
        return "SUCCESS"

    except Exception as e:
        pass
        error_msg = "%s" % e
        logger.info("xmSetupDataStore - Failure stopping MONGOD ...")
        return "FAIL"

if __name__ == '__main__':

    if len(sys.argv) >3:
        for arg in sys.argv[1:]:
            if arg.lower().startswith('host='):
                eqsign = arg.find('=')
                mongo_host = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('port='):
                eqsign = arg.find('=')
                mongo_port = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('authdb='):
                eqsign = arg.find('=')
                mongo_auth_db = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('ssl='):
                eqsign = arg.find('=')
                mongo_ssl = arg[eqsign+1:len(arg)]
            elif arg.lower().startswith('config='):
                eqsign = arg.find('=')
                mongo_config = arg[eqsign+1:len(arg)]
    else:
        raise Exception('xmSetupDataStore-F-001: Usage: xmSetupDataStore host=<string> port=<string> authDB=<string> ssl=<string> config=<string>')

    # Save parameters in scm-framework.properties-default
    logger.info("xmSetupDataStore - saving parameters to properties")
    splunkHome=os.environ.get('SPLUNK_HOME')
    propertyFilename = saUtils.getScmPropertiesFileName()
    tmpFilename = splunkHome + '/etc/apps/bv_xr/config/tmp.csv'

    python3 = sys.version_info[0] >= 3
    rmode = "rb"
    wmode = "wb"
    if python3:
        rmode = "r"
        wmode = "w"

    cfg = cli.getConfStanza('web','settings');
    hostAndPortStr = cfg.get('mgmtHostPort');
    logger.info('mgmtHostPort: ' + hostAndPortStr);
    hostAndPortArr = hostAndPortStr.split(':');
    mgmtPort = hostAndPortArr[1];
    logger.info('Splunk Mgmt Port: ' + mgmtPort);

    with open(propertyFilename, rmode) as propertyFile:
        reader = csv.reader(propertyFile)
        fd = open(tmpFilename, wmode)
        c = csv.writer(fd,lineterminator=os.linesep)
        for row in reader:
            if row:
                 eqsign = row[0].find('=')
                 tmpName = row[0][0:eqsign]
                 if tmpName == "mongo_host":
                     c.writerow(["mongo.host="+mongo_host])
                 elif tmpName == "mongo.host":
                     c.writerow(["mongo.host="+mongo_host])
                 elif tmpName == "mongo.port":
                     c.writerow(["mongo.port="+mongo_port])
                 elif tmpName == "mongo.auth.db":
                     c.writerow(["mongo.auth.db="+mongo_auth_db])
                 elif tmpName == "mongo.ssl":
                     c.writerow(["mongo.ssl="+mongo_ssl])
                 elif tmpName == "mongo.dbpath":
                     mongo_dbpath = row[0][eqsign+1:len(row[0])]
                     c.writerow(row)
                 elif tmpName == "mongo.user":
                     mongo_user = row[0][eqsign+1:len(row[0])]
                     c.writerow(row)
                 elif tmpName == "splunk.rest.ipAddress":
                     c.writerow(["splunk.rest.ipAddress="+mongo_host])
                 elif tmpName == "splunk.rest.port":
                     c.writerow(["splunk.rest.port="+mgmtPort])
                 else:
                     c.writerow(row)
        fd.close()
    shutil.move(tmpFilename, propertyFilename)

    # If port=number present, set value used to override mongo port.
    #overRideMongoPort=-1
    #if len (sys.argv) > 1:
    #    for arg in sys.argv[1:]:
    #        if arg.lower().startswith('port='):
    #            eqsign = arg.find('=')
    #            port = arg [eqsign+1:len(arg)]
    #            if saUtils.isNumber (port):
    #                overRideMongoPort = int(port)
    #            else:
    #                print ("usage: xmSetupDataStore [port=number]")
    #                exit(1)
    #logger.info ("xmSetupDataStore - mongo port override: " + repr(overRideMongoPort))

    print ("Status, Message")
    updateInput = "false" 
    message = ""
    try: 
        # Chmod replication key file, just have permissions 400 (chmod below requires ocatal):
        os.chmod("scm-key-file.txt", 0o400)

        if mongo_config == "standalone":

            # Get mongo properties from scm-framework.properties
            status = set_environment()

            #if status == "FAIL":
            #    logger.info("xmSetupDataStore - Failure Getting Properties (" + error_msg + ")")
            #    #print ("ERROR,FAILURE GETTING PROPERTIES ("+error_msg+")")
            #    message = "FAILURE GETTING PROPERTIES ("+error_msg+")"

            status = is_mongo_running_with_auth()

            if status == "SUCCESS":
                print ("SUCCESS,DATA STORE PREVIOUSLY SETUP AND RUNNING")
                message = "DATA STORE PREVIOUSLY SETUP AND RUNNING"
                logger.info("xmSetupDataStore - MONGOD Previously Setup and Running")
                updateInput = "true"

            elif status == "FAIL":
                status = is_mongo_running_with_no_auth()

                if status == "FAIL":
                    status = start_mongod("FALSE")
                    if status == "FAILURE":
                        #print ("ERROR,FAILURE STARTING MONGOD WITH NO AUTH (" + error_msg + ")")
                        message = "FAILURE STARTING MONGOD WITH NO AUTH (" + error_msg + ")"
                        logger.info("xmSetupDataStore - Failure Starting MONGOD with No Auth")

                if status == "SUCCESS":
                    status = create_user()
                    if status == "SUCCESS" or status == "ALREADY_EXISTS":
                        status = stop_mongod("FALSE")
                        if status == "SUCCESS":
                            updateInput = "true"
                        else:
                            #print ("ERROR,FAILURE STOPPING MONGO (" + error_msg + ")")
                            message = "FAILURE STOPPING MONGO (" + error_msg + ")"
                            logger.info("xmSetupDataStore - Failure Stopping  MONGOD With Auth")

                    else:
                        #print ("ERROR,FAILURE CREATING MONGO USER (" + error_msg + ")")
                        message = "FAILURE CREATING MONGO USER (" + error_msg + ")"
                        logger.info("xmSetupDataStore - Failure Creating MONGO User")

            if status  == "FAILURE":
                print ("FAILURE," + message)
            else:
               if updateInput  == "true":
                   # Ensure scripted input is enabled
                   #settings = saUtils.getSettings(sys.stdin)
                   authString = settings['authString']
                   p = re.compile('<username>(.*)\<\/username>')
                   user= p.search(authString).group(1)

                   endpoint = '/servicesNS/nobody/bv_xr/data/inputs/script/%24SPLUNK_HOME%252Fetc%252Fapps%252Fbv_xr%252Fbin%252FxmRunDataStore.py'
                   postArgs = {'disabled':'0'}
                   response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)

                   if response.status != 200:
                       logger.info("xmSetupDataStore - Failure Enabling Scripted Input, response.status=" + str(response.status))
                       print ("FAILURE, Failure Enabling Scripted Input")
                   else:
                       logger.info("xmSetupDataStore - Success Enabling Scripted Input")
                       print ("SUCCESS," + message)

                   # Check to 
                   counter = 0
                   status = "FAIL"
                   while counter < 10 and status != "SUCCESS":
                       time.sleep(10.0)
                       status = is_mongo_running_with_auth()
                       counter = counter + 1

                   if status == 'SUCCCESS':
                       logger.info("xmSetupDataStore - MONGOD Started Succcessfully with Scripted Input...")
                   else:
                       logger.info("xmSetupDataStore - MONGOD NOT Started Succcessfully with Scripted Input...")

        else:
             # This iis CLOUD deployment, we need to retrieve the splunk key and save it as password.
             # First make sure passwd wasn't  already provisioned (rest api not allowing update)
            logger.info("xmSetupDataStore - Removing Old Password if it exists")
            settings = saUtils.getSettings(sys.stdin)
            endpoint = '/servicesNS/nobody/system/storage/passwords/' + mongo_user
            try:
                response, content = splunk.rest.simpleRequest(endpoint, method='DELETE', sessionKey=settings['sessionKey'], raiseAllErrors=False)
                logger.info("xmSetupDataStore - Delete Response Code: " + str(response.status));
            except Exception as e2:
                logger.warn("xmSetupDataStore - exception deleting user, user may not exist yet.");

            logger.info("xmSetupDataStore - Saving Password")
            splunkHome=os.environ.get('SPLUNK_HOME')
            keyFilename  = splunkHome + '/var/lib/splunk/kvstore/mongo/splunk.key'
            with open(keyFilename, rmode) as keyFile:
                reader = csv.reader(keyFile)
                for row in reader:
                    mongo_password = row[0]

            endpoint = '/servicesNS/nobody/system/storage/passwords'
            postArgs = {'name':mongo_user, 'password':mongo_password}
            response, content = splunk.rest.simpleRequest(endpoint, method='POST', sessionKey=settings['sessionKey'], raiseAllErrors=False, postargs=postArgs)
            logger.info("xmSetupDataStore - Save Response Code: " + str(response.status));

            print  ("SUCCESS")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

        #logger.info("xmSetupDataStore - MAIN EXIT")

    except Exception as e:
        print ("ERROR, %s" % e)
