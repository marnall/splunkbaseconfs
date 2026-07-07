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
import shutil
from tempfile import NamedTemporaryFile
import splunk.Intersplunk as si
from xml.dom import minidom
import json
import splunk.rest
import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')


if __name__ == '__main__':

    try:

        identity=''
        modelName=''

        if len(sys.argv) >1:
            #for arg in sys.argv[1:]:
            identity = sys.argv[1]
            if len(sys.argv) > 2:
                modelName = sys.argv[2]
        else:
            raise Exception('xmDeleteActor-F-001: Usage: xmDeleteActor identity [model]')

        print ('Result')

        db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName())
        collection = db['resource']

        # Look for the actor in the database.
        fromDB = collection.find_one ({"type" : "ACTOR", "primaryId" : identity, "modelName" : modelName })

        if fromDB != None:
            collection.remove ({"_id" : fromDB['_id'] })
            logger.info("xmDeleteActor - Successfully Deleted Actor (identity): " + identity)
            print ("Success")
        else:
            logger.info("xmDeleteActor - Failure Deleting Actor identity: " + identity + ", model: [" + modelName + "]")
            print ("Failure")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

