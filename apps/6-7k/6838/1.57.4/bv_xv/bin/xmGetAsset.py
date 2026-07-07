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

theQuote = '"'

def getPropertyValue (dict,name):
    try:
        if 'properties' in dict:
            return theQuote + dict['properties'][name] + theQuote
    except KeyError:
        # Key is not present
        pass
    return '';

if __name__ == '__main__':
    id = ''
    model = ''
    doExact = False

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('id='):
                    eqsign = arg.find('=')
                    id = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    model = arg[eqsign+1:len(arg)]
                if arg.lower().startswith('exact='):
                    eqsign = arg.find('=')
                    exactArg = arg[eqsign+1:len(arg)]
                    if exactArg.lower() == "true":
                        doExact = True
                    else:
                        doExact = False

        else:
            raise Exception('xmGetAsset-F-001: Usage: xmGetAsset id=<string> [model=<string>]')

        if len(id) == 0:
            raise Exception('xmGetAsset-F-001: Usage: xmGetAsset id=<string>')

        db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName())
        collection = db['resource']

        fromDB = None;

        if doExact == False:

            logger.debug ("Exact=false search, assetId: " + id + ", model: [" + model + "]");

            # Do search that will return a model specific and/or global actor.
            listFromDB = collection.find({ "$and" : [ { "type" : "ASSET" }, { "$or" : [ {"modelName" : model}, {"modelName" : ""} ] }, { "$or" : [ { "primaryId" : id}, { "alternateIds" : { "$in" : [id] }} ] } ] })

            for doc in listFromDB:
                logger.debug ("Found entry in list for actor: " + id + ", model: " + model + repr(doc))
                fromDB = doc;
                # Done if asset model == records modelName... else might be default entry with no modelName.
                if fromDB['modelName'] == model:
                    break;
        else:

            logger.debug ("Exact=true search, assetId: " + id + ", model: [" + model + "]");

            # Look for the asset in the database.
            fromDB = collection.find_one ({"type" : "ASSET", "modelName" : model, "$or" : [ { "primaryId" : id}, { "alternateIds" : { "$in" : [id] }} ]})

        # Asset with the specified primary or alternateId not found in the database.
        if fromDB == None:
            logger.debug ("xmGetAsset - Asset : " + id + " not found!")
            sys.exit (0)

        logger.debug ("Found entry in the DB: [" + repr (fromDB) + "]");

        # Base attributes present for all asset types.
        id = fromDB['primaryId']
        alternateIds = fromDB['alternateIds']
        altIdsList=''
        for i in alternateIds:
            if len(altIdsList) > 0:
                altIdsList += " "
            altIdsList += i
        #logger.debug ("altIds=" + altIdsList)

        modelName = fromDB['modelName']
        type = fromDB['type']
        subType=fromDB['subType']
        criticality=repr (fromDB['criticality'])
        tmpCreateDate = fromDB ['createDate'];
        createDate = str(time.mktime(tmpCreateDate.timetuple()))
        tmpUpdateDate=fromDB ['updateDate']
        updateDate = str(time.mktime(tmpUpdateDate.timetuple()))
        imageId=fromDB['imageId']

        # global properties
        businessUnitProp = getPropertyValue (fromDB, 'businessUnit')
        categoryListProp = getPropertyValue (fromDB, 'categoryList')
        cityProp = getPropertyValue (fromDB, 'city')
        countryProp = getPropertyValue (fromDB, 'country')
        postalCodeProp = getPropertyValue (fromDB,'postalCode')
        gmtOffsetProp = getPropertyValue (fromDB, 'gmtOffset')
        latitudeProp = getPropertyValue (fromDB, 'latitude')
        longitudeProp = getPropertyValue (fromDB,'longitude')
        ownerListProp = getPropertyValue (fromDB, 'ownerList')
        regionProp = getPropertyValue (fromDB,'region')
        stateProp = getPropertyValue (fromDB, 'state')
        tagProp = getPropertyValue (fromDB, 'tag')
        watchListProp = getPropertyValue (fromDB, 'watchList')

        # HUMAN properties
        emailProp = getPropertyValue (fromDB, 'email')
        endDateProp = getPropertyValue (fromDB, 'endDate')
        nameProp = getPropertyValue (fromDB, 'name')
        managedByProp = getPropertyValue (fromDB, 'managedBy')
        phone1Prop = getPropertyValue (fromDB, 'phone1')
        phone2Prop = getPropertyValue (fromDB, 'phone2')
        startDateProp = getPropertyValue (fromDB, 'startDate')
        titleProp = getPropertyValue (fromDB, 'title')

        # MACHINE properties
        cpuSpeedGhzProp = getPropertyValue (fromDB, 'cpuSpeedGhz')
        dnsListProp = getPropertyValue (fromDB, 'dnsList')
        hostnameProp = getPropertyValue (fromDB, 'hostname')
        ipListProp = getPropertyValue (fromDB, 'ipList')
        macProp = getPropertyValue (fromDB, 'mac')
        memorySizeMBProp = getPropertyValue (fromDB, 'memorySizeMB')
        numCPUsProp = getPropertyValue (fromDB, 'numCPUs')
        osTypeProp = getPropertyValue (fromDB, 'osType')
        osVersionProp = getPropertyValue (fromDB, 'osVersion')
        pciDomainProp = getPropertyValue (fromDB, 'pciDomain')

        if subType == 'HUMAN':
            print ('id,alternateIds,type,subtype,criticality,createDate,updateDate,imageId,businessUnit,categoryList,city,country,gmtOffset,latitude,longitude,ownerList,region,state,tag,watchList,email,endDate,name,managedBy,phone1,phone2,startDate,title, postalCode, modelName')
            print (id + "," + altIdsList + "," + type + "," + subType + "," + criticality + "," + createDate + "," + updateDate + "," + imageId + "," + businessUnitProp + "," + categoryListProp + "," + cityProp + "," + countryProp + "," + gmtOffsetProp + "," + latitudeProp + "," + longitudeProp + "," + ownerListProp + "," + regionProp + "," + stateProp + "," + tagProp + "," + watchListProp + "," + emailProp + "," + endDateProp + "," + nameProp + "," + managedByProp + "," + phone1Prop + "," + phone2Prop + "," + startDateProp + "," + titleProp + "," + postalCodeProp + "," + modelName)

        elif subType == 'MACHINE':
            print ('id,alternateIds,type,subtype,criticality,createDate,updateDate,imageId,businessUnit,categoryList,city,country,gmtOffset,latitude,longitude,ownerList,region,state,tag,watchList,cpuSpeedGhz,dnsList,hostname,ipList,mac,memorySizeMB,numCPUs,osType,osVersion,pciDomain, postalCode, modelName')
            print (id + "," + altIdsList + "," + type + "," + subType + "," + criticality + "," + createDate + "," + updateDate + "," + imageId +  "," + businessUnitProp + "," + categoryListProp + "," + cityProp + "," + countryProp + "," + gmtOffsetProp + "," + latitudeProp + "," + longitudeProp + "," + ownerListProp + "," + regionProp + "," + stateProp + "," + tagProp + "," + watchListProp + "," + cpuSpeedGhzProp + "," + dnsListProp + "," + hostnameProp + "," + ipListProp + "," + macProp + "," + memorySizeMBProp + "," + numCPUsProp + "," + osTypeProp + "," + osVersionProp + "," + pciDomainProp + "," + postalCodeProp + "," + modelName)

        elif subType == 'DISCOVERED':
            print ('id,alternateIds,type,subtype,criticality,createDate,updateDate,imageId,businessUnit,categoryList,city,country,gmtOffset,latitude,longitude,ownerList,region,state,tag,watchList, postalCode, modelName')
            print (id + "," + altIdsList + "," + type + "," + subType + "," + criticality + "," + createDate + "," + updateDate + "," + imageId + "," + businessUnitProp + "," + categoryListProp + "," + cityProp + "," + countryProp + "," + gmtOffsetProp + "," + latitudeProp + "," + longitudeProp + "," + ownerListProp + "," + regionProp + "," + stateProp + "," + tagProp + "," + watchListProp + "," + postalCodeProp + "," + modelName)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

        logger.info("xmGetAsset - Successfully Retrieved Asset: [" + id + "], modelName: [" + modelName + "]");

    except Exception as e:
        si.generateErrorResults(e)

