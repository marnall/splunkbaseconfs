# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import datetime
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
    # core
    id= ''
    newId= ''
    newModel= ''
    alternateIds= ''
    modelName=''
    type = ''
    subtype = ''
    createDate = ''
    updateDate = ''
    criticality = ''
    imageId = ''

    # GLOBAL
    businessUnit = ''
    categoryList = ''
    city = ''
    country = ''
    postalCode = ''
    gmtOffset = ''
    latitude = ''
    longitude = ''
    ownerList = ''
    region = ''
    state = ''
    tag = ''
    watchList = ''

    # HUMAN properties
    endDate = ''
    email = ''
    name = ''
    managedBy = ''
    phone1 = ''
    phone2 = ''
    startDate = ''
    title = ''

    # MACHINE properties
    cpuSpeedGhz = ''
    dnsList = ''
    hostname = ''
    ipList = ''
    mac = ''
    memorySizeMB = ''
    numCPUs = ''
    osType = ''
    osVersion = ''
    pciDomain = ''

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                # CORE
                if arg.lower().startswith('id='):
                    eqsign = arg.find('=')
                    id = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('newid='):
                    eqsign = arg.find('=')
                    newId = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('alternateids='):
                    eqsign = arg.find('=')
                    alternateIds = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    modelName = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('newmodel='):
                    eqsign = arg.find('=')
                    newModel = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('type='):
                    eqsign = arg.find('=')
                    type = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('subtype='):
                    eqsign = arg.find('=')
                    subtype = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('createdate='):
                    eqsign = arg.find('=')
                    createDate = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('updatedate='):
                    eqsign = arg.find('=')
                    updateDate = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('criticality='):
                    eqsign = arg.find('=')
                    criticality = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('imageid='):
                    eqsign = arg.find('=')
                    imageId = arg[eqsign+1:len(arg)]
                # GLOBAL
                elif arg.lower().startswith('businessunit='):
                    eqsign = arg.find('=')
                    businessUnit = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('categorylist='):
                    eqsign = arg.find('=')
                    categoryList = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('city='):
                    eqsign = arg.find('=')
                    city = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('country='):
                    eqsign = arg.find('=')
                    country = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('postalcode='):
                    eqsign = arg.find('=')
                    postalCode = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('gmtoffset='):
                    eqsign = arg.find('=')
                    gmtOffset = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('latitude='):
                    eqsign = arg.find('=')
                    latitude = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('longitude='):
                    eqsign = arg.find('=')
                    longitude = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('ownerlist='):
                    eqsign = arg.find('=')
                    ownerList = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('region='):
                    eqsign = arg.find('=')
                    region = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('state='):
                    eqsign = arg.find('=')
                    state = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('tag='):
                    eqsign = arg.find('=')
                    tag = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('watchlist='):
                    eqsign = arg.find('=')
                    watchList = arg[eqsign+1:len(arg)]
                # HUMAN
                elif arg.lower().startswith('email='):
                    eqsign = arg.find('=')
                    email = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('enddate='):
                    eqsign = arg.find('=')
                    endDate = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('name='):
                    eqsign = arg.find('=')
                    name = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('managedby='):
                    eqsign = arg.find('=')
                    managedBy = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('phone1='):
                    eqsign = arg.find('=')
                    phone1 = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('phone2='):
                    eqsign = arg.find('=')
                    phone2 = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('startdate='):
                    eqsign = arg.find('=')
                    startDate = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('title='):
                    eqsign = arg.find('=')
                    title = arg[eqsign+1:len(arg)]
                # MACHINE
                elif arg.lower().startswith('cpuspeedghz='):
                    eqsign = arg.find('=')
                    cpuSpeedGhz = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('dnslist='):
                    eqsign = arg.find('=')
                    dnsList = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('hostname='):
                    eqsign = arg.find('=')
                    hostname = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('iplist='):
                    eqsign = arg.find('=')
                    ipList = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('mac='):
                    eqsign = arg.find('=')
                    mac = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('memorysizemb='):
                    eqsign = arg.find('=')
                    memorySizeMB = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('numcpus='):
                    eqsign = arg.find('=')
                    numCPUs = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('ostype='):
                    eqsign = arg.find('=')
                    osType = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('osversion='):
                    eqsign = arg.find('=')
                    osVersion = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('pcidomain='):
                    eqsign = arg.find('=')
                    pciDomain = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmSetAsset-F-001: Usage: xmSetAsset id=<string> alternateids=<string> model=<string> newid=<string> newmodel=<string> type=<string> subtype=<string> criticality=<string> [createdate=<string>] [updatedate=<string>] [imageid=<string>] [businessunit=<string>] [categorylist=<string>] [city=<string>] [country=<string>] [postalcode=<string>] [gmtOffset=<string>] [latitude=<string>] [longitude=<string>] [ownerlist=<string>] [region=<string>] [state=<string>] [tag=<string>] [watchlist=<string>] [dateofbirth=<string>] [enddate=<string>] [email=<string>] [name=<string>] [managedby=<string>] [phone1=<string>] [phone2=<string>] [startdate=<string>] [title=<string>] [cpuspeedghz=<string>] [dnslist=<string>] [hostname=<string>] [iplist=<string>] [mac=<string>] [memorysizemb=<string>] [numcpus=<string>] [ostype=<string>] [osversion=<string>] [pcidomain=<string>] [description=<string] [name=<string>')

        if id == '' and newId == '':
            raise Exception("xmSetAsset-F-001: parameter 'id' or 'newid' not found")
        if type == '':
            raise Exception("xmSetAsset-F-001: parameter 'type' not found")
        if subtype == '':
            raise Exception("xmSetAsset-F-001: parameter 'subtype' not found")
        if createDate == '':
            raise Exception("xmSetAsset-F-001: parameter 'createdate' not found")
        if updateDate == '':
            raise Exception("xmSetAsset-F-001: parameter 'updatedate' not found")
        if criticality == '':
            raise Exception("xmSetAsset-F-001: parameter 'criticality' not found")

        if subtype == 'HUMAN':
            if name == '':
                raise Exception("xmSetAsset-F-001: parameter 'name' not found")

        if subtype == 'MACHINE':
            if hostname == '':
                raise Exception("xmSetAsset-F-001: parameter 'hostname' not found")

        #logger.info ("Received arguments, id: [" + id + "], newId: [" + newId + "], alternateIds: [" + alternateIds + "], modelName: [" + modelName + "], type: [" + type + "], subType: [" + subtype + "], createDate: [" + createDate + "], updateDate: [" + updateDate + "], criticality: [" + criticality + "], imageId: [" + imageId + "]");

        db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName())
        collection = db['resource']

        print ("Result")

        # Assign alternateIds to array, needed for the insert and update case as the mongo object stores these as an array.
        alternateIdList = []
        if alternateIds != "":
            alternateIdList = alternateIds.split()
            logger.info ("Splitting alternateIds into list of " + repr (len(alternateIdList)) + " items")

        # Check Duplicate ID
        checkForDuplicate = "false"
        alreadyExists = "false"
        if id == '' and newId != '':
            # CREATE
            checkForDuplicate = "true"
            logger.info ("1) CreateAsset:  id == '' and newId != ''");
        elif id != '' and id != newId:
            checkForDuplicate = "true"
            logger.info ("2) UpdateAsset: id != '' and id != newId");
        elif modelName != newModel:
            checkForDuplicate = "true"
            logger.info ("3) UpdateAsset: modelName != newModelName");
        else:  # no need to check to see if the Id already exists, updating existing actor and not changing Id or modelName.
            logger.info ("No need to see if duplicate exists, updating existing asset's attributes")

        # Look for the asset in the database by either primaryId or alternateIds
        fromDB = collection.find_one ({"type" : "ASSET", "modelName" : newModel, "$or" : [ { "primaryId" : newId}, { "alternateIds" : { "$in" : [newId] }} ]})

       # TODO: Need to validate alternateIds are not already in use by a DIFFERENT user... possibly do this below.

        if checkForDuplicate == "true":

            logger.info ("Looking up asset with id: [" + newId + "] and model [" + newModel + "]")

            # Asset with the specified primary or alternateId not found in the database.
            if fromDB != None:
                logger.info("xmGetAsset - Asset: [" + id + "] and model: [" + newModel + "] already exists!")
                alreadyExists = "true"
                print ("ALREADY_EXISTS")
            else:
               logger.info ("ASSET [" + newId + "] DOES NOT EXIST!")

        # If creating new asset or updating existing (w/out changing Id)
        if alreadyExists != "true":

            logger.info ("alreadyExists != true") 

            #=======================================================================
            # Determine if another asset with specified alternateIds already exists.
            #=======================================================================
            for curAltId in alternateIdList:
                assetWithAltId = collection.find_one ({"type" : "ASSET", "modelName" : newModel, "$or" : [ { "primaryId" : curAltId}, { "alternateIds" : { "$in" : [curAltId] }} ]})
                if assetWithAltId != None:
                    if fromDB != None:
                        if fromDB ['_id'] != assetWithAltId ['_id']:
                            logger.info ("Found asset that already uses alternateId: [" + curAltId + "], asset: [" + assetWithAltId['primaryId'] + "], modelName: [" + newModel + "]")
                            print ("Failure")
                            exit(1)
                    else:
                        logger.info ("Found asset that already uses alternateId: [" + curAltId + "], asset: [" + assetWithAltId ['primaryId'] + "]")
                        print ("Failure")
                        exit(1)

            # If the asset's identifiers (id and/or modelName) changed but existing actor not found, need to lookup the actor to update.
            if fromDB == None:
                fromDB = collection.find_one ({"type" : "ASSET", "modelName" : modelName, "$or" : [ { "primaryId" : id}, { "alternateIds" : { "$in" : [id] }} ]})
                if fromDB == None:
                    logger.error ("ERROR - Expecting to perform an update but failed to find exsiting asset with id: [" + id + "], modelName: [" + modelName + "]");
                else:
                    logger.info ("Found asset to update, primaryId: [" + id + "], modelName: [" + modelName + "], _id: [" + repr (fromDB['_id']) + "]");

            properties = {}

            # Core properties which can be present on all asset types.
            properties ['businessUnit'] = businessUnit
            properties ['categoryList'] = categoryList 
            properties ['city'] = city 
            properties ['country'] = country 
            properties ['gmtOffset'] = gmtOffset 
            properties ['latitude'] = latitude 
            properties ['longitude'] = longitude 
            properties ['ownerList'] = ownerList 
            properties ['region'] = region
            properties ['state'] = state 
            properties ['tag'] = tag 
            properties ['watchList'] = watchList 
            properties ['postalCode'] = postalCode

            if subtype == 'HUMAN':

                logger.debug ("sub-type HUMAN...") 

                properties ['email'] = email
                properties ['endDate'] = endDate
                properties ['name'] = name
                properties ['managedBy']  = managedBy 
                properties ['phone1'] = phone1 
                properties ['phone2'] = phone2 
                properties ['startDate'] = startDate 
                properties ['title'] = title 

            elif subtype == 'MACHINE':

                logger.debug ("sub-type MACHINE...") 

                properties ['cpuSpeedGhz'] =  cpuSpeedGhz 
                properties ['dnsList'] = dnsList 
                properties ['hostname'] = hostname
                properties ['ipList'] = ipList 
                properties ['mac'] = mac 
                properties ['memorySizeMB'] = memorySizeMB
                properties ['numCPUs'] =  numCPUs 
                properties ['osType']  = osType;
                properties ['osVersion'] = osVersion 
                properties ['pciDomain'] = pciDomain 

            elif subtype == 'DISCOVERED':

                logger.debug ("sub-type DISCOVERED...") 

            if fromDB != None: 

                # Update existing asset

                logger.info ("Updating asset with primaryId: [" + newId + "], alternateIds: [" + alternateIds + "], modelName: [" + newModel + "], type: [" + type + "], subType: [" + subtype + "], criticality: [" + criticality + "], createDate: [" + createDate + "], updateDate: [" + updateDate + "], imageId: [" + imageId + "], properties: [" + repr(properties) + "]");

                collection.update_one ({ '_id' : fromDB['_id'] },{ '$set' : { 'primaryId' : newId, 'alternateIds' : alternateIdList, 'modelName' : newModel, 'type' : type, 'subType' : subtype, 'criticality' : int(criticality), 'updateDate' : datetime.datetime.utcnow(), 'imageId' : imageId, 'properties' : properties }}, upsert=False)

            else: 

                # Insert new asset

                logger.info ("Creating new asset with primaryId: [" + newId + "], alternateIds: [" + alternateIds + "], modelName: [" + modelName + "], type: [" + type + "], subType: [" + subtype + "], criticality: [" + criticality + "], createDate: [" + createDate + "], updateDate: [" + updateDate + "], imageId: [" + imageId + "], properties: [" + repr(properties) + "]");

                collection.insert_one ({ 'primaryId' : newId, 'alternateIds' : alternateIdList, 'modelName' : modelName, 'type' : type, 'subType' : subtype, 'criticality' : int(criticality), 'createDate' : datetime.datetime.utcnow(), 'updateDate' : datetime.datetime.utcnow(), 'imageId' : imageId, 'properties' : properties});

            print ("Success")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)
