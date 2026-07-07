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

""" An adapter that takes CSV as input, performs a lookup to mongo for assets.
"""

assetIds = {}

# Given a host, find the ip
def lookup(collection, assetId, modelName, row):

    if len(assetId) == 0:
        return

    if len(modelName) == 0:
        return

    asset = None
    if assetId in assetIds:
        logger.debug ("Key for " + assetId + " exists in cache!")
        asset = assetIds[assetId]
    else:
        logger.debug("Key for " + assetId + " DOES NOT exist!")

        #fromDB = collection.find_one ({"type" : "ASSET", "modelName" : modelName, "$or" : [ { "primaryId" : assetId}, { "alternateIds" : { "$in" : [assetId] }} ]})

        # Look for the asset in the database.
        listFromDB = collection.find({ "$and" : [ { "type" : "ASSET" }, { "$or" : [ {"modelName" : modelName}, {"modelName" : ""} ] }, { "$or" : [ { "primaryId" : assetId}, { "alternateIds" : { "$in" : [assetId] }} ] } ] })

        fromDB = None
        for doc in listFromDB:
            logger.debug ("Found entry in list for asset: " + assetId + ", model: " + modelName + repr(doc))
            fromDB = doc;
            # Done if asset modelName == record's modelName... else might be default entry with no modelName.
            if fromDB['modelName'] == modelName:
                break;

        if fromDB == None:
            logger.warn ("external_lookup_asset - Asset: " + assetId + " NOT FOUND in DB!")
            fromDB = {}
            fromDB['subType'] = "UNDEFINED"
            fromDB['criticality'] = 0
            fromDB['imageId'] = ""
        else:
            logger.info (" Asset: " + assetId+ ", Criticality: " + repr (fromDB['criticality']) + " FOUND in DB!")
 
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

        asset = {}
        asset ['subType'] = fromDB['subType']
        if 'alternateIds' in fromDB:
            asset ['alternateIds'] = altIdsList
        asset ['criticality'] = fromDB['criticality']
        if 'imageId' in fromDB:
            asset ['imageId'] = fromDB['imageId']
        asset ['properties'] = propertiesList
        assetIds [assetId] = asset

    # 'id', 'subType', 'alternateIds', 'criticality', 'imageId', 'properties
    row ['subType'] = asset['subType']
    if 'alternateIds' in asset:
        row ['alternateIds'] = asset['alternateIds']
    row ['criticality'] = asset['criticality']
    if 'imageId' in asset:
        row ['imageId'] = asset['imageId']
    row ['properties'] = asset['properties']

def main():

    if len(sys.argv) != 3:
        print ("Usage: python external_lookup_asset.py [assetIdField] [modelNameField]")
        logger.error ("Usage, unexpected number of arguments (expecting 3): " + repr(sys.argv))
        sys.exit(1)

    db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName())
    collection = db['resource']

    logger.debug ("external_lookup_asset starting, received arguments: " + repr(sys.argv))

    assetIdField = sys.argv[1]
    modelNameField = sys.argv[2]

    logger.debug ("assetIdField=" + assetIdField + ",  modelNameField=" + modelNameField)

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
        if result[assetIdField] and result[modelNameField]:
            logger.debug ("assetIdField: " + assetIdField + " and modelNameField: " + modelNameField + " exists!")
            assetId = result[assetIdField]
            modelName = result[modelNameField]
            logger.debug ("AssetId: " + assetId + ", modelName: " + modelName)
            lookup (collection, assetId, modelName, result)
            w.writerow(result)
        else:
            logger.error ("MISSING assetIdField: [" + inputField + "]")
        numProcessed += 1

    logger.debug ("external_lookup_asset exiting, processed " + repr (numProcessed) + " records")

main()
