# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import saDbUtils
from pymongo import MongoClient
import datetime
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

import datetime

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
    modelName = ''
    doExact = False

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('id='):
                    eqsign = arg.find('=')
                    id = arg[eqsign+1:len(arg)]
                if arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    modelName = arg[eqsign+1:len(arg)]
                if arg.lower().startswith('exact='):
                    eqsign = arg.find('=')
                    exactArg = arg[eqsign+1:len(arg)]
                    if exactArg.lower() == "true":
                        doExact = True
                    else:
                        doExact = False
        else:
            raise Exception('xmGetActor-F-001: Usage: xmGetActor id=<string>')

        db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName())
        collection = db['resource']

        fromDB = None;

        if doExact == False:

            # Do search that will return a model specific and/or global actor.
            listFromDB = collection.find({ "$and" : [ { "type" : "ACTOR" }, { "$or" : [ {"modelName" : modelName}, {"modelName" : ""} ] }, { "$or" : [ { "primaryId" : id}, { "alternateIds" : { "$in" : [id] }} ] } ] })

            for doc in listFromDB:
                logger.debug ("Found entry in list for actor: " + id + ", model: " + modelName + repr(doc))
                fromDB = doc;
                # Done if actor modelName == records modelName... else might be default entry with no modelName.
                if fromDB['modelName'] == modelName:
                    break;
        else:
            # Look exact lookup for the actor in the database.
            fromDB = collection.find_one ({"type" : "ACTOR", "modelName" : modelName, "$or" : [ { "primaryId" : id}, { "alternateIds" : { "$in" : [id] }} ]})

        # Actor with the specified primary or alternateId not found in the database.
        if fromDB == None:
            logger.info("xmGetActor - Actor: " + id + ", modelName: " + modelName + " not found!")
            sys.exit (0)

        # Base attributes present for all actor types.
        id = fromDB['primaryId']
        modelName = fromDB['modelName']

        alternateIds = []
        if 'alternateIds' in fromDB:
            alternateIds = fromDB['alternateIds']
        altIdsList=''
        for i in alternateIds:
            if len(altIdsList) > 0:
                altIdsList += " "
            altIdsList += i
        #logger.debug ("altIds=" + altIdsList)

        type = fromDB['type']
        subType=fromDB['subType']
        criticality=repr (fromDB['criticality'])
        tmpCreateDate = fromDB ['createDate'];
        createDate = str(time.mktime(tmpCreateDate.timetuple()))
        tmpUpdateDate=fromDB ['updateDate']
        updateDate = str(time.mktime(tmpUpdateDate.timetuple()))
        imageId = ''
        if 'imageId' in fromDB:
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
        managedByProp = getPropertyValue (fromDB, 'managedBy')
        nameProp = getPropertyValue (fromDB, 'name')
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

        # SERVICE properties
        descriptionProp = getPropertyValue (fromDB, 'description')
        serviceNameProp = getPropertyValue (fromDB, 'serviceName')

        if subType == 'HUMAN':
            print ('id,alternateIds,type,subtype,criticality,createDate,updateDate,imageId,businessUnit,categoryList,city,country,gmtOffset,latitude,longitude,ownerList,region,state,tag,watchList,email,endDate,name,managedBy,phone1,phone2,startDate,title,postalCode,modelName')
            print (id + "," + altIdsList + "," + type + "," + subType + "," + criticality + "," + createDate + "," + updateDate + "," + imageId + "," + businessUnitProp + "," + categoryListProp + "," + cityProp + "," + countryProp + "," + gmtOffsetProp + "," + latitudeProp + "," + longitudeProp + "," + ownerListProp + "," + regionProp + "," + stateProp + "," + tagProp + "," + watchListProp + "," + emailProp + "," + endDateProp + "," + nameProp + "," + managedByProp + "," + phone1Prop + "," + phone2Prop + "," + startDateProp + "," + titleProp + "," + postalCodeProp + "," + modelName)

        elif subType == 'MACHINE':
            print ('id,alternateIds,type,subtype,criticality,createDate,updateDate,imageId,businessUnit,categoryList,city,country,gmtOffset,latitude,longitude,ownerList,region,state,tag,watchList,cpuSpeedGhz,dnsList,hostname,ipList,mac,memorySizeMB,numCPUs,osType,osVersion,pciDomain,postalCode,modelName')
            print (id + "," + altIdsList + "," + type + "," + subType + "," + criticality + "," + createDate + "," + updateDate + "," + imageId +  "," + businessUnitProp + "," + categoryListProp + "," + cityProp + "," + countryProp + "," + gmtOffsetProp + "," + latitudeProp + "," + longitudeProp + "," + ownerListProp + "," + regionProp + "," + stateProp + "," + tagProp + "," + watchListProp + "," + cpuSpeedGhzProp + "," + dnsListProp + "," + hostnameProp + "," + ipListProp + "," + macProp + "," + memorySizeMBProp + "," + numCPUsProp + "," + osTypeProp + "," + osVersionProp + "," + pciDomainProp + "," + postalCodeProp + "," + modelName)

        elif subType == 'SERVICE':
            print ('id,alternateIds,type,subtype,criticality,createDate,updateDate,imageId,businessUnit,categoryList,city,country,gmtOffset,latitude,longitude,ownerList,region,state,tag,watchList,descriptionProp,serviceNameProp,postalCode,modelName')
            print (id + "," + altIdsList + "," + type + "," + subType + "," + criticality + "," + createDate + "," + updateDate + "," + imageId + "," + businessUnitProp + "," + categoryListProp + "," + cityProp + "," + countryProp + "," + gmtOffsetProp + "," + latitudeProp + "," + longitudeProp + "," + ownerListProp + "," + regionProp + "," + stateProp + "," + tagProp + "," + watchListProp + "," + descriptionProp + "," + serviceNameProp + "," + postalCodeProp + "," + modelName)

        elif subType == 'DISCOVERED':
            print ('id,alternateIds,type,subtype,criticality,createDate,updateDate,imageId,businessUnit,categoryList,city,country,gmtOffset,latitude,longitude,ownerList,region,state,tag,watchList,postalCode,modelName')
            print (id + "," + altIdsList + "," + type + "," + subType + "," + criticality + "," + createDate + "," + updateDate + "," + imageId + "," + businessUnitProp + "," + categoryListProp + "," + cityProp + "," + countryProp + "," + gmtOffsetProp + "," + latitudeProp + "," + longitudeProp + "," + ownerListProp + "," + regionProp + "," + stateProp + "," + tagProp + "," + watchListProp + "," + postalCodeProp + "," + modelName)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

        logger.info("xmGetActor - Successfully Retrieved Actor: " + id + ", modelName: " + modelName)

    except Exception as e:
        si.generateErrorResults(e)

