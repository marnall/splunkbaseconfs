# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import os,platform,time
import subprocess
import sys
import platform
import time
import re
import json
import splunk.Intersplunk as si
import saDbUtils
import saUtils
import splunk.rest

import logging as logger
from io import open
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

mongo_host = ''
mongo_port = ''
mongo_db = ''
mongo_auth_db = ''
mongo_user = ''
mongo_password = ''
mongo_dbpath = ''
splunkHome = ''
mongo_binary = ''
ldpath_mongo = ''
ldpath_mongod = ''
ldpath_splunk_bin = ''
useauth = 'FALSE'

if __name__ == '__main__':

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('useauth='):
                    eqsign = arg.find('=')
                    useauth = arg[eqsign+1:len(arg)]
                    useauth = useauth.lower()
        else:
            raise Exception('xmVerifyDataStore-F-001: Usage: xmVerifyDataStore useauth=<string>')

        print ("Status, Message")


        with open(saUtils.getScmPropertiesFileName()) as propertyFile:
            for line in propertyFile:
                propname, propval = line.partition("=")[::2]
                if propname.strip() == "mongo.host":
                    mongo_host = propval[:-1]
                elif propname.strip() == "mongo.port":
                    mongo_port = propval[:-1]
                elif propname.strip() == "mongo.db":
                    mongo_db = propval[:-1]
                elif propname.strip() == "mongo.auth.db":
                    mongo_auth_db = propval[:-1]
                elif propname.strip() == "mongo.user":
                    mongo_user = propval[:-1]
                elif propname.strip() == "mongo.dbpath":
                    mongo_dbpath= propval[:-1]

        # Retrieve password from splunk storage
        settings = saUtils.getSettings(sys.stdin)
        passwdEndpoint = "/services/storage/passwords/" + mongo_user + "?output_mode=json"
        passwdResponse, passwdContent = splunk.rest.simpleRequest (passwdEndpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)
        tmp = json.loads(passwdContent)
        mongo_password = tmp['entry'][0]['content']['clear_password']

        # Splunk Version determines which version of Mongo
        serverEndpoint = "/services/server/info?output_mode=json"
        serverResponse, serverContent = splunk.rest.simpleRequest (serverEndpoint, method='GET', sessionKey=sessionKey, raiseAllErrors=False)
        tmp = json.loads(serverContent)
        version = tmp['entry'][0]['content']['version']
        logger.info ("xmVerifyDataStore - Splunk Version: " + version)
        versionList = version.split(".")
        m_version = versionList[0];
        logger.info ("xmVerifyDataStore - Is Splunk Version >= " + versionList[0])

        splunkHome=os.environ.get('SPLUNK_HOME')
        ldpath_mongo = os.path.normpath (splunkHome + "/etc/apps/bv_xv/lib")
        ldpath_mongod = os.path.normpath (splunkHome + "/lib")
        ldpath_splunk_bin = os.path.normpath (splunkHome + '/bin')

        mongo_dbpath = mongo_dbpath.replace("$(SPLUNK_HOME)",splunkHome)
        #logger.info("xmVerifyDataStore - RETRIEVED PROPERTIES")

        #mongo_binary = splunkHome + '/etc/apps/bv_xv/bin/' +  platform.system() + '/' + platform.architecture()[0] + '/mongo'
        if int(m_version) >= 9:
            mongo_binary = './' +  platform.system() + '/' + platform.architecture()[0] + '/mongo4'
        else:
            mongo_binary = './' +  platform.system() + '/' + platform.architecture()[0] + '/mongo'


        if (platform.system() == 'Windows'):
            mongo_binary = mongo_binary + ".exe"
            saUtils.addToPath (ldpath_mongo)
            saUtils.addToPath (ldpath_mongod)
            saUtils.addToPath (ldpath_splunk_bin)

        if not os.path.isfile(mongo_binary):
            raise Exception("xmRunDataStore-F-000: Can't find binary file " + mongo_binary)

        #ldpath = splunkHome + "/etc/apps/bv_xv/lib"
        #ldpath_mongo = splunkHome + "/etc/apps/bv_xv/lib"
        #ldpath_mongod = splunkHome + "/lib"

        if useauth == "true":
            cmd = mongo_binary + ' -u ' + mongo_user + " -p " + mongo_password + " -authenticationDatabase " + mongo_auth_db + " --quiet --host " + mongo_host + " --port " + mongo_port + " --eval \"db.runCommand({ping:1})\""
            if (platform.system() == 'Darwin'):
                if os.getenv('DYLD_LIBRARY_PATH')  == None:
                    os.environ["DYLD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
                else:
                    os.environ["DYLD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo
                cmd = "export DYLD_LIBRARY_PATH=\""+ldpath_mongo+"\"; "+cmd
            else:
                if os.getenv('LD_LIBRARY_PATH')  == None:
                    os.environ["LD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
                else:
                    os.environ["LD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo

            mongo_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
            logger.info("xmVerifyDataStore - DATA STORE IS RUNNING (TESTED WITH AUTH)")
            print ("SUCCESS, DATA STORE IS RUNNING (TESTED WITH AUTH)")
        else:
            cmd = mongo_binary + ' --quiet --host ' + mongo_host + ' --port ' + mongo_port + ' --eval "db.runCommand({ping:1})"'
            if (platform.system() == 'Darwin'):
                if os.getenv('DYLD_LIBRARY_PATH')  == None:
                    os.environ["DYLD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
                else:
                    os.environ["DYLD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo
                cmd = "export DYLD_LIBRARY_PATH=\""+ldpath_mongo+"\"; "+cmd
            else:
                if os.getenv('LD_LIBRARY_PATH')  == None:
                    os.environ["LD_LIBRARY_PATH"] = os.pathsep + ldpath_mongo
                else:
                    os.environ["LD_LIBRARY_PATH"] += os.pathsep + ldpath_mongo

            #logger.info("xmVerifyDataStore - CHECK MONGOD (NO AUTH) CMD: " + cmd)
            mongo_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)

            logger.info("xmVerifyDataStore - DATA STORE IS RUNNING (TESTED WITH NO AUTH)")
            print ("SUCCESS, DATA STORE IS RUNNING (TESTED WITH NO AUTH)")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)


    except Exception as e:
        #logger.info("xmVerifyDataStore - EXCEPTION:  " + str(e.output))
        logger.info("xmVerifyDataStore - DATA STORE IS NOT RUNNING")
        print ("FAILURE, DATA STORE IS NOT RUNNING")

