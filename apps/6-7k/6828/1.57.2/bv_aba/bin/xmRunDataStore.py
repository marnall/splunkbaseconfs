# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import os,platform
import subprocess
import signal
import sys
import re
import time
#import splunk.Intersplunk as si
import saUtils
import saDbUtils
import shutil
import splunk.rest
import json

import logging as logger
from io import open
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

class GracefulKiller:
    kill_now = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self,signum, frame):
        self.kill_now = True

if __name__ == '__main__':
    mongo_host = ''
    mongo_port = ''
    mongo_db = ''
    mongo_auth_db = ''
    mongo_user = ''
    mongo_password = ''
    mongo_dbpath = ''
    mongo_replicaSet_hosts = ''
    mongo_replicaSet_name = ''
    replicaSetConfig = ''
    #redirect_output = ">/dev/null 2>&1 &"
    redirect_output = ">/dev/null 2>&1"
    cmdPrefix = ''
    pid = 0
    print ("Status")


    try: 
        killer = GracefulKiller()
        logger.info("xmRunDataStore - Get mongo properties");
        # Get mongo properties
        with open(saUtils.getScmPropertiesFileName()) as propertyFile:
            for line in propertyFile:
                propname, propval = line.partition("=")[::2]
                if propname.strip() == "mongo.host":
                    mongo_host = propval[:-1].rstrip()
                elif propname.strip() == "mongo.port":
                    mongo_port = propval[:-1].rstrip()
                elif propname.strip() == "mongo.db":
                    mongo_db = propval[:-1].rstrip()
                elif propname.strip() == "mongo.auth.db":
                    mongo_auth_db = propval[:-1].rstrip()
                elif propname.strip() == "mongo.user":
                    mongo_user = propval[:-1].rstrip()
                    #mongo_user = propval[:end]
                elif propname.strip() == "mongo.dbpath":
                    mongo_dbpath= propval[:-1].rstrip()
                elif propname.strip() == "mongo.replicaSet.hosts":
                    mongo_replicaSet_hosts = propval[:-1].rstrip()
                elif propname.strip() == "mongo.replicaSet.name":
                    mongo_replicaSet_name = propval[:-1].rstrip()

        sessionKey = sys.stdin.readline().strip()

        # Retrieve "scm" password from splunk storage
        passwdEndpoint = "/services/storage/passwords/" + mongo_user.rstrip() + "?output_mode=json"
        passwdResponse, passwdContent = splunk.rest.simpleRequest (passwdEndpoint, method='GET', sessionKey=sessionKey, raiseAllErrors=False)
        tmp = json.loads(passwdContent)
        mongo_password = tmp['entry'][0]['content']['clear_password']

        # Splunk Version determines which version of Mongo
        serverEndpoint = "/services/server/info?output_mode=json"
        serverResponse, serverContent = splunk.rest.simpleRequest (serverEndpoint, method='GET', sessionKey=sessionKey, raiseAllErrors=False)
        tmp = json.loads(serverContent)
        version = tmp['entry'][0]['content']['version']
        logger.info ("xmRunDataStore - Splunk Version: " + version)
        versionList = version.split(".")
        m_version = versionList[0];
        logger.info ("xmRunDataStore - Is Splunk Version >= " + versionList[0])

        splunkHome=os.environ.get('SPLUNK_HOME')
        mongo_dbpath = os.path.normpath (mongo_dbpath.replace("$(SPLUNK_HOME)",splunkHome))

        if not os.path.exists(mongo_dbpath):
            os.makedirs(mongo_dbpath);

        # Migration for Cloud Certification, move $SPLUNK_HOME/var/lib/scm -> $SPLUNK_HOME/etc/apps/bv_aba/scm
        # After the app starts all properties will be updated by a DB Migration to reference this new directory.
        if "var" in mongo_dbpath:
            old_scm_dir = "$(SPLUNK_HOME)/var/lib/scm"
            old_scm_dir = os.path.normpath (old_scm_dir.replace("$(SPLUNK_HOME)",splunkHome))
            new_scm_home = "$(SPLUNK_HOME)/etc/apps/bv_aba"
            new_scm_home = os.path.normpath (new_scm_home.replace("$(SPLUNK_HOME)",splunkHome))
            logger.info ("xmRunDataStore - Running DB migration, mongo_dbpath: " + mongo_dbpath + ", moving [" + old_scm_dir + "] => [" + new_scm_home + "], new mongo_dbpath [" + mongo_dbpath + "]");
            shutil.move (old_scm_dir, new_scm_home);
            # Over-ride mongo_dbpath to reference new DB file location
            mongo_dbpath = os.path.normpath (new_scm_home + "/scm/db");

        ldpath_mongo = os.path.normpath (splunkHome + "/etc/apps/bv_aba/lib")
        ldpath_mongod = os.path.normpath (splunkHome + "/lib")
        logger.info("xmRunDataStore - ldpath_mongo=" + ldpath_mongo)
        logger.info("xmRunDataStore - ldpath_mongod=" + ldpath_mongod)

        if (platform.system() == 'Darwin'):
            saUtils.addToLDLibraryPath (ldpath_mongo);
        else:
            saUtils.addToLDLibraryPath (ldpath_mongod);
            saUtils.addToLDLibraryPath (ldpath_mongo);

        saUtils.addToPath (ldpath_mongo)
        saUtils.addToPath (ldpath_mongod)

        #
        # If mongo_replicaSet_hosts is set then the app is expecting the DB to be running with replication enabled.
        #
        # --replSet scm --keyFile scm-key-file.txt
        if len(mongo_replicaSet_hosts) > 0 and len(mongo_replicaSet_name) > 0:
            replicaSetConfig = " --replSet " + mongo_replicaSet_name + " --keyFile scm-key-file.txt ";

        #mongo_binary = splunkHome + '/etc/apps/bv_aba/bin/' +  platform.system() + '/' + platform.architecture()[0] + '/mongo'
        #mongo_binary = './' +  platform.system() + '/' + platform.architecture()[0] + '/mongo'
        if int(m_version) >= 9:
            mongo_binary = splunkHome + '/etc/apps/bv_aba/bin/' +  platform.system() + '/' + platform.architecture()[0] + '/mongo4'
        else:
            mongo_binary = splunkHome + '/etc/apps/bv_aba/bin/' +  platform.system() + '/' + platform.architecture()[0] + '/mongo'

        if (platform.system() == 'Windows'):
            mongo_binary = mongo_binary + ".exe"
            redirect_output = ' > NUL 2>&1'
            cmdPrefix = 'START /B '

        mongo_binary = os.path.normpath (mongo_binary)

        if not os.path.isfile(mongo_binary):
            raise Exception("xmRunDataStore-F-000: Can't find binary file " + mongo_binary)

        cmd = mongo_binary + ' -u ' + mongo_user + ' -p ' + mongo_password + ' -authenticationDatabase ' + mongo_auth_db + ' --host ' + mongo_host + ' --port ' + mongo_port + ' --eval "db.runCommand({ping:1})"'

        if (platform.system() == 'Darwin'):
            cmd = "export DYLD_LIBRARY_PATH=\""+ldpath_mongo+"\"; " + '"' + mongo_binary + '" -u ' + mongo_user + ' -p ' + mongo_password + ' -authenticationDatabase ' + mongo_auth_db + ' --host ' + mongo_host + ' --port ' + mongo_port + ' --eval "db.runCommand({ping:1})"'

        try:
            mongo_output = subprocess.check_output(cmd, shell=True)
   
            # an exception is thrown if mongo not running 
            print ("MONGOD RUNNING")
            #logger.info("cmd output " + mongo_output);
            logger.info("xmRunDataStore - MONGOD RUNNING");

        except Exception as e:
            pass
            binary = os.path.normpath(splunkHome + '/bin/mongod')

            if (platform.system() == 'Windows'):
                binary = binary + ".exe"

            if not os.path.isfile(binary):
                raise Exception("xmRunDataStore-F-000: Can't find binary file " + binary)

            if (platform.system() == 'Darwin'):
                if os.getenv('DYLD_LIBRARY_PATH')  == None:
                    os.environ["DYLD_LIBRARY_PATH"] = os.pathsep +  ldpath_mongod
                else:
                    os.environ["DYLD_LIBRARY_PATH"] += os.pathsep +  ldpath_mongod
            else:
                if os.getenv('LD_LIBRARY_PATH')  == None:
                    os.environ["LD_LIBRARY_PATH"] = os.pathsep + ldpath_mongod
                else:
                    os.environ["LD_LIBRARY_PATH"] += os.pathsep + ldpath_mongod

            #cmd = binary + " --auth --bind_ip " + mongo_host + " --port " + mongo_port + " --dbpath " + mongo_dbpath  + " >/dev/null 2>&1 &"

            #retcode = os.system(cmd);
            #cmd = binary + ' --auth --port ' + mongo_port + ' --dbpath "' + mongo_dbpath  + '"' + replicaSetConfig + ' >/dev/null 2>&1 &'
            #cmd = cmdPrefix + binary + ' --bind_ip 0.0.0.0 --auth --port ' + mongo_port + ' --dbpath "' + mongo_dbpath  + '"' + replicaSetConfig + redirect_output
            cmd = '\"' + binary + '\" --bind_ip 0.0.0.0 --auth --port ' + mongo_port + ' --dbpath "' + mongo_dbpath  + '"' + replicaSetConfig + redirect_output

            if len(replicaSetConfig) > 0:
                logger.info("xmRunDataStore - replication mode enabled, using parameters: " + replicaSetConfig);
            else:
                logger.info("xmRunDataStore - NOT running in replication mode");

            if (platform.system() == 'Windows'):
                pid = subprocess.Popen(cmd,shell=True).pid
            else:
                pid = subprocess.Popen("exec " + cmd,shell=True).pid

            logger.info("xmRunDataStore - MONGOD STARTED pid=" + str(pid));
            print ("MONGOD STARTED")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

        while True:
            try:
                if platform.system() == 'Linux':
                    ppid = os.getppid()
                    if ppid == 1:
                        logger.info("xmRunDataStore - killing ... ");
                        os.kill(pid, signal.SIGTERM)
                        break
                if killer.kill_now:
                    logger.info("xmRunDataStore - Splunk Shutting Down - Stopping Mongo");
                    os.kill(pid, signal.SIGTERM)
                    break
                time.sleep(5.0)
            except Exception as e:
                logger.info("xmRunDataStore - Failure Stopping Mongo - Exception: %s" % e); 

    except Exception as e:
        logger.info("xmRunDataStore - MONGO NOT RUNNING due to Exception: %s" % e); 
        print ("FAILURE")
