# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import saDbUtils
from pymongo import MongoClient
import fnmatch
import os
import platform
import time
import re
import csv
import sys
import saUtils
import splunk.Intersplunk as si
from xml.dom import minidom
import json
#from xml.dom.minidom import parseString
import splunk.rest

import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    idlist = ''
    modelName = ''
    foundlist = []
    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('idlist='):
                    eqsign = arg.find('=')
                    idlist = arg[eqsign+1:len(arg)].split(",")
                elif arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    modelName = arg[eqsign+1:len(arg)]
        #else:
            #raise Exception('xmVerifyActors-F-001: Usage: xmVerifyActors idlist=<string>')

        db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName())
        collection = db['resource']

        print ('id')

        totalCount = 0
        foundCount = 0

        for id in idlist:
            totalCount = totalCount + 1
            count = collection.find ({"type" : "ACTOR", "modelName" : modelName, "$or" : [ { "primaryId" : id}, { "alternateIds" : { "$in" : [id] }} ]}).count()
            if count == 0:
                # The actor does not exist, output the actorId
                print (id)
            else:
                # The actor exists
                foundCount = foundCount + 1

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

        logger.info("xmVerifyActors - Found " + str(foundCount) + " out of " + str(totalCount))

    except Exception as e:
        si.generateErrorResults(e)

