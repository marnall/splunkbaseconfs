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
import splunk.Intersplunk as si
from xml.dom import minidom
import json
import splunk.rest

import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

#theQuote = '"'

def getPropertyValue (dict,name):
    try:
        #return theQuote + dict['properties'][name] + theQuote
        return dict['properties'][name]
    except KeyError:
        # Key is not present
        pass
    return '';

if __name__ == '__main__':
    identity = ''
    name = ''
    bunit = ''
    tag = ''
    category = ''
    criticality = ''
    watchlist = ''
    type = ''
    model = '*'

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('name='):
                    eqsign = arg.find('=')
                    name = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('bunit='):
                    eqsign = arg.find('=')
                    bunit = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('identity='):
                    eqsign = arg.find('=')
                    identity = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('category='):
                    eqsign = arg.find('=')
                    if category == '*':
                      category = arg[eqsign+1:len(arg)]
                    else:
                      category += " " +arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('criticality='):
                    eqsign = arg.find('=')
                    criticality = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('watchlist='):
                    eqsign = arg.find('=')
                    watchlist = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('type='):
                    eqsign = arg.find('=')
                    type = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('tag='):
                    eqsign = arg.find('=')
                    tag = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    model = arg[eqsign+1:len(arg)]
        #else:
            #raise Exception('xmListActors-F-001: Usage: xmListActors [identity=<string>] [name=<string>] [bunit=<string>] [category=<string>][criticality=<string>] [tag=<string>] [watchlist=<string>] [type=<string>]')

        identity = identity.strip()
        category = category.strip()
        businessUnit = category.strip()
        name = name.strip()
        bunit = bunit.strip()
        tag = tag.strip()
        criticality = criticality.strip()
        watchlist = watchlist.strip()
        type = type.strip()
        model = model.strip()

        # The UI passes '*' in attributes to indicate ALL values are acceptable,
        # clear the argument if '*' is present since we are doing DB search.
        if category == "*":
            category=''
        if bunit == "*":
             bunit =''
        if name == "*":
             name =''
        if tag == "*":
             tag =''
        if criticality == "*":
             criticality =''
        if watchlist == "*":
             watchlist =''
        if type == "*":
             type =''

        logger.info ("args: identity=[" + identity + "], category=[" + category + "], bunit=[" + bunit + "], name=[" + name + "], tag=[" + tag + "], criticality=[" + criticality + "], watchlist=[" + watchlist + "], type=[" + type + "], model=[" + model + "]")

        db = saDbUtils.connectToDb (saUtils.getScmPropertiesFileName())
        collection = db['resource']

        query='{ "type" : "ACTOR"'
        if len(identity) > 0:
            query += ', "$or" : [ { "primaryId" : "' + identity + '"}, { "alternateIds" : { "$in" : ["' + identity + '"] }} ]'

        # Global actors or modelName == ""
        if model == '*':
            # All models
            logger.debug ("Looking for actors from all models")
        elif len(model) == 0:
            # Global actors where modelName == ""
            logger.debug ("Looking for actors global actors where modelName = ''")
            query += ', "modelName" : ""'
        elif len(model) > 0:
            # Specific model
            logger.debug ("Looking for actors from model: '" + model + "'")
            query += ', "modelName" : "' + model + '"'

        if len(name) > 0:
            query += ', "properties.name" : "' + name + '"'
        if len(bunit) > 0:
            query += ', "properties.businessUnit" : "' + bunit + '"'
        if len(tag) > 0:
            query += ', "properties.tag" : "' + tag + '"'
        #if len(category) > 0:
        #    query += ', "properties.categoryList" : "' + category + '"'
        if len(criticality) > 0:
            query += ', "criticality" : ' + criticality
        if len(watchlist) > 0:
            query += ', "properties.watchList" : "' + watchlist + '"'
        if len(type) > 0:
            query += ', "subType" : "' + type + '"' 
        query += "}"

        logger.debug ("xmListActors - query: " + query)

        # Convert query string to JSON object
        jsonQuery = json.loads(query)

        logger.debug ("Converted query to json object..")

        print ('id, alternateIds, name, subtype, bunit, category, criticality, tag, watchlist, modelName')

        # Run query and process results, additional filtering may occur depending on which arguments are supplied
        for record in collection.find (jsonQuery):

            # Global properties
            primaryId = ''
            altIdsStr = ''
            modelName = ''
            # possible properties
            businessUnitProp = ''
            categoryProp = ''
            emailProp = ''
            endDateProp = ''
            nameProp = ''
            managedByProp = ''
            phone1Prop = ''
            phone2Prop = ''
            startDateProp = ''
            titleProp = ''
            watchListProp = ''
            tagProp = ''

            primaryId = record ['primaryId']
            subType = record ['subType']
            if 'modelName' in record:
                modelName = record ['modelName']
            criticality = str (record ['criticality'])

            #if record.has_key ('alternateIds'):
            if 'alternateIds' in record:
                for altId in record['alternateIds']:
                    logger.debug ("Found altId: " + altId);
                    if len(altIdsStr) > 0: altIdsStr += " "
                    altIdsStr += altId

            nameProp = getPropertyValue (record, 'name')
            hostnameProp = getPropertyValue (record, 'hostname')
            businessUnitProp = getPropertyValue (record, 'businessUnit')
            categoryProp = getPropertyValue (record, 'categoryList')
            watchListProp = getPropertyValue (record, 'watchList')
            tagProp = getPropertyValue (record, 'tag')

            #logger.debug ("Found record primaryId: " + primaryId + ", altIds: " + altIdsStr + ", name: " + name + 
            #              ", firstName: " + firstNameProp + ", lastName: " + lastNameProp + ", businessUnit: " + 
            #              businessUnitProp)

            # Default watchList to false if not preset.
            if len(watchListProp) == 0:
                watchListProp = 'false';

            # Combind actor name attributes into single output field.
            if len(hostnameProp) == 0:
                actorName = nameProp
            else:
                actorName = hostnameProp

            if len(name) > 0 and name != actorName:
                logger.debug ("Actor name specified and name: [" + name + "] != actorName: [" + actorName + "]")
                continue

            foundCat = "false"
            if len(category) > 0:
                # Loop over each category argument supplied (there can be more than one).
                categoryArg = category.split(' ');
                categoryList = categoryProp.split(' ');
                for tmpCategoryArg in categoryArg:
                    # Loop over each of the actors categories
                    for tmpCategory in categoryList:
                        logger.debug ("comparing tempCategory: [" + tmpCategory + "] with category to match: [" + category + "]")
#                        if tmpCategory.lower() == category.lower():
                        if tmpCategory.lower() == tmpCategoryArg.lower():
                            logger.debug ("category matches!")
                            foundCat = "true"
                            break
                        else:
                            logger.debug ("category DOES NOT MATCH!")
                            foundCat = "false"
                    if foundCat == "true":
                        break;

            if len(category) > 0 and foundCat == "false":
                logger.debug ("Catgory specified but not found for actor: [" + actorName + "], cateory to find: [" + category + "], categoryList: [" + categoryProp + "]") 
                continue

            # TODO FIX
            # Output the row.
            print ('"' + primaryId + '","' + altIdsStr + '","' + actorName + '","' + subType + '","' + businessUnitProp + '","' + categoryProp.replace('\n',' ') + '","' + criticality + '","' + tagProp + '","' + watchListProp + '","' + modelName + '"')
        logger.debug ("xmListActors - queryDone!")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)
