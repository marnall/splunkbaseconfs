#!/usr/bin/env python
# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import saDbUtils
import saUtils
from pymongo import MongoClient
import fnmatch
import os
import re
import csv
import sys
import socket

import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

""" An adapter that takes CSV as input, performs a lookup to mongo for SCM actors.
"""

actorIds = {}

# Given a host, find the ip
def lookup(collection, actorId, modelName, row):

    if len(actorId) == 0:
        return

    if len(modelName) == 0:
        return

    actor = None
    if actorId in actorIds:
        logger.debug ("Key for " + actorId + " exists in cache!")
        actor = actorIds[actorId]
    else:
        logger.debug("Key for " + actorId + " DOES NOT exist!")

        # Look for the actor in the database.
        listFromDB = collection.find({ "$and" : [ { "type" : "ACTOR" }, { "$or" : [ {"modelName" : modelName}, {"modelName" : ""} ] }, { "$or" : [ { "primaryId" : actorId}, { "alternateIds" : { "$in" : [actorId] }} ] } ] })

        fromDB = None
        for doc in listFromDB:
            logger.debug ("Found First entry in list for actor: " + actorId + ", model: " + modelName + repr(doc))
            fromDB = doc;
            # Done if actor modelName == records modelName... else might be default entry with no modelName.
            if fromDB['modelName'] == modelName:
                break;

        if fromDB == None:
            logger.warn ("external_lookup_actor - Actor: " + actorId + " NOT FOUND in DB!")
            fromDB = {}
            fromDB['subType'] = "UNDEFINED"
            fromDB['criticality'] = 0
            fromDB['imageId'] = ""
        else:
            logger.debug (" Actor: " + actorId + ", Criticality: " + repr (fromDB['criticality']) + " FOUND in DB!")
 
       # Convert AlternateIds from array to string.
        altIdsList=''
        if 'alternateIds' in fromDB:
            alternateIds = fromDB['alternateIds']
            for i in alternateIds:
                if len(altIdsList) > 0:
                    altIdsList += "|"
                altIdsList += i

        logger.debug ("altIds=" + altIdsList)

       # Convert properties from map to string.
        propertiesList=''
        if 'properties' in fromDB:
            properties = fromDB['properties']
            for i in properties:
                if len(propertiesList) > 0:
                    propertiesList += "|"
                propertyName = i
                propertyValue = fromDB ['properties'][propertyName]
                propertiesList += propertyName + '=' + propertyValue

        logger.debug ("properties=" + propertiesList)

        actor = {}
        actor ['subType'] = fromDB['subType']
        if 'alternateIds' in fromDB:
            actor ['alternateIds'] = altIdsList
        actor ['criticality'] = fromDB['criticality']
        if 'imageId' in fromDB:
            actor ['imageId'] = fromDB['imageId']
        actor ['properties'] = propertiesList
        actorIds [actorId] = actor

    # 'id', 'subType', 'alternateIds', 'criticality', 'imageId', 'properties
    row ['subType'] = actor['subType']
    if 'alternateIds' in actor:
        row ['alternateIds'] = actor['alternateIds']
    row ['criticality'] = actor['criticality']
    if 'imageId' in actor:
        row ['imageId'] = actor['imageId']
    row ['properties'] = actor['properties']

def main():

    if len(sys.argv) != 3:
        print ("Usage: python external_lookup.py [actorIdField] [modelNameField]")
        logger.error ("Usage, unexpected number of arguments (expecting 3): " + repr(sys.argv))
        sys.exit(1)

    db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName())
    collection = db['resource']

    logger.debug ("external_lookup_actor starting, received arguments: " + repr(sys.argv))

    actorIdField = sys.argv[1]
    modelNameField = sys.argv[2]

    logger.debug ("actorIdField=" + actorIdField + ",  modelNameField=" + modelNameField)

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    logger.debug ("CSV Header: " + repr(header))

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    numProcessed = 0
    for result in r:
        #logger.info ('read row')
        if result[actorIdField] and result[modelNameField]:
            logger.debug ("actorIdField: " + actorIdField + " and modelNameField: " + modelNameField + " exists!")
            actorId = result[actorIdField]
            modelName = result[modelNameField]
            logger.debug ("ActorId: " + actorId + ", modelName: " + modelName)
            lookup (collection, actorId, modelName, result)
            w.writerow(result)
        else:
            logger.error ("MISSING actorIdField: [" + inputField + "]")
        numProcessed += 1

    logger.debug ("external_lookup_actor exiting, processed " + repr (numProcessed) + " records")

main()
