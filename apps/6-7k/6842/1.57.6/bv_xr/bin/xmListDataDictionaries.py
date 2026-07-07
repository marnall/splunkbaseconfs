# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import saDbUtils
import time
import fnmatch
import os
import platform
import re
import csv
import sys
import saUtils
import splunk.Intersplunk as si
from xml.dom import minidom
import json
from collections import namedtuple
import splunk.rest

import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')


if __name__ == '__main__':
    model = ''
    app = ''
    rowPerField = 'false'
    try:

        if len(sys.argv) == 2:
            if sys.argv[1].lower() == 'fields':
                rowPerField = 'true'
    
        print ('name, description, datamodel, datamodelobject, keyColumnName, keyColumnValue, columnValueCompare, actor, action, process, field, key')

        db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName())
        collection = db['config']

        # Look-up the data dictionary document from the config collection.
        dictionaryConfig = collection.find_one ({"type" : "DATA_DICTIONARY"})

        logger.debug ("Loaded dictionary record: " + repr (dictionaryConfig))

        if dictionaryConfig != None:
            data = dictionaryConfig['data']
            logger.debug ("Loaded dictionary: " + repr (data))

            dictionary = []

            for e in data[u'dictionary']:
                #dictionary.append(namedtuple('dictionary', e.keys())(*e.values()))
                dictionary.append(namedtuple('dictionary', list(e.keys()))(*list(e.values())))

            for tmp in dictionary:
                description = ''
                actor = ''
                action = ''
                process = ''
                key = ''

                dd = tmp.DataDefinition
                if 'description' in list(dd.keys()):
                    description = dd['description']
                if 'action' in list(dd.keys()):
                    action = dd['action']
                if 'process' in list(dd.keys()):
                    process = dd['process']
                if 'key' in list(dd.keys()):
                    key = dd['key']
                else:
                    key = ''
                if 'actorId' in list(dd.keys()):
                    actor = dd['actorId']
                fieldList = []
                fieldString = ''
                for fd in dd['fields']:
                    field = fd['FieldDefinition']
                    #fieldString = fieldString + field['name'] + " "
                    taxonomyType = field['taxonomyType']
                    if taxonomyType == 'ACTION':
                        action = field['name']
                    elif taxonomyType == 'ACTOR':
                        actor = field['name']
                    elif taxonomyType == 'PROCESS':
                        process = field['name']
                    elif taxonomyType == 'FIELD':
                        fieldList.append(field['name'])
                        fieldString = fieldString + field['name'] + " "
                    elif taxonomyType == 'FIELD_VALUE':
                        fieldList.append(field['name'])
                        fieldString = fieldString + field['name'] + " "
                    elif taxonomyType == 'FIELD_CONCEPT_LOOKUP':
                        fieldList.append(field['name'])
                        fieldString = fieldString + field['name'] + " "
                    elif taxonomyType == 'KEY':
                        key = field['name']

                if rowPerField == 'true':
                    for f in fieldList:
                        print (dd['name'] + ",\"" +  description + "\"," + dd['dataModel'] + ",\"" + dd['dataModelObject'] + "\"," + dd['keyColumnName'] + ",\"" + dd['keyColumnValue'] + "\"," + dd['columnValueCompare'] + "," + actor + "," + action + "," + process + "," + f + "," + key)
                else:
                    print (dd['name'] + ",\"" +  description + "\"," + dd['dataModel'] + ",\"" + dd['dataModelObject'] + "\"," + dd['keyColumnName'] + ",\"" + dd['keyColumnValue'] + "\"," + dd['columnValueCompare'] + "," + actor + "," + action + "," + process + "," + fieldString + "," + key)

        else:
           logger.info ("Failed to find DataDictionary entry in the config collection")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)
