# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import saDbUtils
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
    # core
    id= ''
    alternateId= ''
    alternateIds= ''

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('id='):
                    eqsign = arg.find('=')
                    id = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('alternateid='):
                    eqsign = arg.find('=')
                    alternateId = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('type='):
                    eqsign = arg.find('=')
                    type = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmAddAlternateId-F-001: Usage: xmAddAlternateId id=<string> alternateid=<string> type=<string>')

        if id == '':
            raise Exception("xmAddAlternateId-F-001: parameter 'id' not found")
        if alternateId  == '':
            raise Exception("xmAddAlternateId-F-001: parameter 'alternateId' not found")
        if type == '':
            raise Exception("xmAddAlternateId-F-001: parameter 'type' not found")

        db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName())
        collection = db['resource']

        Result = "Success";

        if type != 'ACTOR' and type != 'ASSET':
            raise Exception("xmAddAlternateId-F-001: invalid 'type' specified, must be ACTOR or ASSET")

        print ("Result")

        # Find the record to update in the database
        fromDB = collection.find_one ({"type" : type, "primaryId" : id})

        # Asset with the specified primary or alternateId not found in the database.
        if fromDB == None:
            logger.error ("xmAddAlternateId - " + type + " with Id: " + id + " not found!")
            print ("Failure")
            sys.exit (0)

        logger.debug ("xmAddAlternateId - Found record with type: " + type + ", ID: " + repr(fromDB['_id']) + " - " + fromDB['primaryId']);

        # See if the alternateId is already in use as a primaryId or alternateId for a different actor
        existingRecordWithAltId = collection.find_one ({"type" : type, "$or" : [ { "primaryId" : alternateId}, { "alternateIds" : { "$in" : [alternateId] }} ]})

        if existingRecordWithAltId != None:
            if existingRecordWithAltId ["_id"] == fromDB ["_id"]:
                logger.info ("xmAddAlternateId - AlternateId: " + alternateId + " already exists on the specified actor: " + fromDB["primaryId"]);
                print ("Success")
                sys.exit (0)
            else:
                logger.error ("xmAddAlternateId - AlternateId " + alternateId + " for " + type + " already in use by resource with Id: " + existingRecordWithAltId["primaryId"])
                print ("Failure")
                sys.exit (0)
        else:
            logger.debug ("xmAddAlternateId - AlternateId " + alternateId + " for " + type + " not yet in use, adding alternateId to existing record") 

        mongoId = fromDB['_id']
        alternateIds = fromDB ['alternateIds']
        alternateIds.append (alternateId);

        logger.debug ("xmAddAlternateId - Updating mongo object with Id: " + repr (mongoId) + " with alternateId: [" + alternateId + "]")
        collection.update_one({"_id": mongoId}, {"$set": {"alternateIds" : alternateIds}}, upsert=False)

        print ("Success")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

