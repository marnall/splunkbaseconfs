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

        modelName=''
        fromDB=''

        if len(sys.argv) >1:
            #for arg in sys.argv[1:]:
            modelName = sys.argv[1]
        else:
            raise Exception('xmResetActors-F-001: Usage: xmResetResources [model]')

        print ('Result')

        db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName())
        collection = db['resource']

        # Look for the actor in the database.
        if modelName == '':
            #fromDB = collection.remove ({})
            fromDB = collection.delete_many ({})
        else:
            #fromDB = collection.remove ({"modelName" : modelName })
            fromDB = collection.delete_one ({"modelName" : modelName })

        print ("Success")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

