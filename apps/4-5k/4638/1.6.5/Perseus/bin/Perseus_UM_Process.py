#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import six

import Splunk_Main as SM
import Splunk_Search
import Splunk_KV_Store
import Splunk_Management
import Perseus_Management_Log

import sys

VISIBILITY_KV_STORE_NAME = "UnauthorizedModsEventVisibility"
EXCEPTIONS_KV_STORE_NAME = "UnauthorizedModsEventExceptions"
EXCEPTIONS_MASTER1_LOOKUP_NAME = "UnauthorizedModsEventMasterExceptions1"
EXCEPTIONS_MASTER2_LOOKUP_NAME = "UnauthorizedModsEventMasterExceptions2"

VISIBILITY_FIELD_NAME = "nVisibility"
VISIBILITY_KEY_FIELD_NAME = "_key"
USER_FIELD_NAME = "_user"

EXCEPTION_KEY_FIELD_NAME = "_key"

EARLIEST_CMD_ARG_LC = "-earliest"
INDEX_EARLIEST_CMD_ARG_LC = "-index_earliest"
EXCEPTION_KV_STORE_KEY_CMD_ARG_LC = "-exceptionkey"
INSTALL_KV_STORE_KEY_CMD_ARG_LC = "-installkey"
RECREATE_CMD_ARG_LC = "-recreate"

#We map the field names to short strings for faster comparisons because there are potentially millions of comparisons

#NOTE: If you add to this map, make sure you modify the other map and append the pre-processing that uses this map below as well
dictExceptionFieldMap = { "strEventID" : 1,
                          "strLocGuid" : 2,
                          "nLocEntryType" : 3,
                          "strLocEntryName" : 4,
                          "strLocEntryData" : 5,
                          "strLocAEFMD5" : 6,
                          "strHostGuid" : 7 }

EXCEPTION_FIELD_MAP_LOC_ENTRY_NAME_VALUE = dictExceptionFieldMap["strLocEntryName"]
EXCEPTION_FIELD_MAP_LOC_GUID_VALUE = dictExceptionFieldMap["strLocGuid"]

#These are fields we either won't ever need for comparison or haven't implemented exception-processing for
#!TFinish - OPTIONAL - "strHostID" is only included for backwards compatibility. We can remove this at some point in the future
lstExceptionFieldsToIgnore = [ "_key", "_user", "strLocUser", "strLocEntryOriginalData", "strLocAEFRawString", "strInstallKey", "nVisibility", "dtCreationDate", "strSplunkUser", "strHostID" ]

#NOTE: If you add to this map, make sure you modify the other map and append the search query in getEventsToProcessForVisibility below as well
dictEventFieldMap = { "Event.ID" : 1,
                      "Event.LocMod.Location.LocGuid" : 2,
                      "Event.LocMod.LocEntry.EntryType" : 3,
                      "Event.LocMod.LocEntry.EntryName" : 4,
                      "Event.LocMod.LocEntry.EntryData" : 5,
                      "Event.LocMod.LocEntry.AutoExecFiles.AutoExecFile.AEFAttributes.AEFAttribute.AEFAttrMD5" : 6,
                      "host" : 7 }

EVENT_FIELD_MAP_EVENT_ID_VALUE = dictEventFieldMap["Event.ID"]
EVENT_FIELD_MAP_LOC_GUID_VALUE = dictEventFieldMap["Event.LocMod.Location.LocGuid"]

def processCommandLine():

    dictCommandLine = {}

    for nArg in range(1, len(sys.argv)):
        strArgLC = sys.argv[nArg].lower()

        #No value argument
        if (strArgLC == RECREATE_CMD_ARG_LC):
            dictCommandLine[strArgLC] = ""
        #Single value argument
        elif ((strArgLC == EARLIEST_CMD_ARG_LC) or (strArgLC == INDEX_EARLIEST_CMD_ARG_LC) or (strArgLC == EXCEPTION_KV_STORE_KEY_CMD_ARG_LC) or (strArgLC == INSTALL_KV_STORE_KEY_CMD_ARG_LC)):
            nArg += 1
            dictCommandLine[strArgLC] = sys.argv[nArg]

    return dictCommandLine

def getUnauthorizedModsEventExceptionsList():
    strQuery = " | inputlookup " + EXCEPTIONS_KV_STORE_NAME + " | append [ | inputlookup " + EXCEPTIONS_MASTER1_LOOKUP_NAME + " ] | append [ | inputlookup " + EXCEPTIONS_MASTER2_LOOKUP_NAME + " ]"
    query = Splunk_Search.SplunkSearchQuery(strQuery, False)
    return query.executeQueryAndGetJsonResults()

def getEventVisibility(eventIn, lstEventExceptionsPreprocessedIn):

    nVisibility = 0
    for eventException in lstEventExceptionsPreprocessedIn:

        #!TFinish - OPTIONAL - For now all UnauthorizedModsEventExceptions have a visibility value of 1 and we optimize to take advantage of this. If we change this in the future, update this to reflect that by reading the visibility value from the exception
        #!TFinish - OPTIONAL - Entries from the master exceptions list should have a different value so we don't reprocess them when a whitelist entry is removed
        nVisibility = 1
        
        #The pre-processed exception field value is a lower case value split on the wildcard character *
        for nKey, lstSplitValue in six.iteritems(eventException):

            try:
                #The event is pre-processed to be a lower case string
                strEventValue = eventIn[nKey]
            except:
                
                #Check for a match on a blank Entry Name (the field will not exist)
                #We store a blank entry name as (Default), so (Default) indicates a match of the blank Entry Name

                if ((nKey == EXCEPTION_FIELD_MAP_LOC_ENTRY_NAME_VALUE) and (lstSplitValue[0] == "(default)")):
                    continue
                #If the field does not exist in the event, then it can't possibly be a match
                else:
                    nVisibility = 0
                    break
                
            if (len(lstSplitValue) == 1):                         
                if (strEventValue != lstSplitValue[0]):
                    nVisibility = 0
                    break

            #!TFinish - OPTIONAL PERFORMANCE - There are likely ways to increase wildcard comparison performance if we deem it necessary
            else:

                nCurrentIndex = 0
                #This was already split on the wildcard character * during preprocessing
                nParts = len(lstSplitValue)

                bMatch = False
                for nCurrentPart in range(0, nParts):
                    strPart = lstSplitValue[nCurrentPart]
                    
                    #Handle initial wildcard by skipping to the next part to match
                    if ((nCurrentPart == 0) and (len(strPart) == 0)):
                        continue
                    #Handle final character wildcard indicating we matched successfully
                    elif ((nCurrentPart == (nParts - 1)) and (len(strPart) == 0)):
                        bMatch = True

                    nCurrentIndex = strEventValue.find(strPart, nCurrentIndex)
                    
                    #We failed to match a part, break out of the loop indicating no match
                    if (nCurrentIndex == -1):
                        break
                    #Move the index along to account for the 
                    else:
                        nCurrentIndex += len(strPart)

                    #If we matched the final part, we have matched the string
                    if (nCurrentPart == (nParts - 1)):
                        bMatch = True

                if (not bMatch):
                    nVisibility = 0
                    break

        #This event matched an exception, so it will not be visible. We don't have to enumerate any of the other exceptions
        if (nVisibility != 0):
            break

    return nVisibility

def getEventsToProcessForVisibility(dictCmdArgsIn):

    strTimeQuery = ""

    #If time bounds are passed to the function, modify the time portion of the query
    if (EARLIEST_CMD_ARG_LC in dictCmdArgsIn):
        strTimeQuery = "earliest=" + dictCmdArgsIn[EARLIEST_CMD_ARG_LC]
    elif (INDEX_EARLIEST_CMD_ARG_LC in dictCmdArgsIn):
        strTimeQuery = "_index_earliest=" + dictCmdArgsIn[INDEX_EARLIEST_CMD_ARG_LC]

    strTableQuery = ""
    strRenameQuery = ""
    
    for strKey, nValue in six.iteritems(dictEventFieldMap):
        if (strTableQuery):
            strTableQuery += ", "
            strRenameQuery += ", "
        else:
            strTableQuery += " | table "
            strRenameQuery = " | rename "

        strTableQuery += str(nValue)
        strRenameQuery += '"' + strKey + '" AS "' + str(nValue) + '"'
        
    bAppendSearch = True
    #NOTE: I had to add | eval Event.ID = mvindex('Event.ID', 0) to resolve a case where an entry mistakenly contains multiple Event.ID. If we validate data before adding it to the index, we could eliminate this requirement
    #!TFinish (NEXT RELEASE) - We now include permit in list of events to whitelist because we can filter by approved in Recollection. Make sure there weren't any disadvantages to doing this
    strSearchQuery = ('`PerseusIndex` (Event.LocMod.LocModType="permit" OR Event.LocMod.LocModType="audit" OR Event.LocMod.LocModType="block") ' + strTimeQuery +
                      ' | eval Event.ID = mvindex(\'Event.ID\', 0) | lookup ' + VISIBILITY_KV_STORE_NAME + ' ' + VISIBILITY_KEY_FIELD_NAME + ' AS Event.ID OUTPUT ' + VISIBILITY_FIELD_NAME + ' | where isnull(' + VISIBILITY_FIELD_NAME + ')' +
                      strRenameQuery + strTableQuery)

    #Handle Perseus Demo which requires prepending with | and modifying the time query
    if (SM.IS_PERSEUS_DEMO):
        bAppendSearch = False
        strSearchQuery = " | " + strSearchQuery
        
        nEqualIndex = strTimeQuery.find("=")
        if (nEqualIndex != -1):
            strNewTimeQuery = "_time >" + strTimeQuery[nEqualIndex:] + " "
            strSearchQuery = strSearchQuery.replace(strTimeQuery, strNewTimeQuery)

    query = Splunk_Search.SplunkSearchQuery(strSearchQuery, bAppendSearch)
    jsonResults = query.executeQueryAndGetJsonResults()

    return jsonResults

def getEventVisibilityKVStoreEntry(strEventIDIn, strVisibilityIn):        
    return { VISIBILITY_KEY_FIELD_NAME : strEventIDIn, VISIBILITY_FIELD_NAME : strVisibilityIn }
    
def addEventVisibilityEntriesToKVStore(lstEntriesIn):
    kvVisibility = Splunk_KV_Store.SplunkKVStore(VISIBILITY_KV_STORE_NAME)
    kvVisibility.addEntry(lstEntriesIn)

def clearEventVisibilityKVStore():
    kvVisibility = Splunk_KV_Store.SplunkKVStore(VISIBILITY_KV_STORE_NAME)
    kvVisibility.removeAllEntries()
    
def processEventVisibility(dictCmdArgsIn):
    
    lstEventExceptions = getUnauthorizedModsEventExceptionsList()

    bRecreated = False
    
    try:
        strExceptionLC = dictCmdArgsIn[EXCEPTION_KV_STORE_KEY_CMD_ARG_LC].lower()
        bExceptionKeyProvided = True
    except:
        bExceptionKeyProvided = False
        
    try:
        strInstallKeyLC = dictCmdArgsIn[INSTALL_KV_STORE_KEY_CMD_ARG_LC].lower()
        bInstallKeyProvided = True
    except:
        bInstallKeyProvided = False
    
    #Only handle a specific (usually newly added) exception or Install-based exceptions
    if (bExceptionKeyProvided or bInstallKeyProvided):
        lstEventExceptionsCopy = lstEventExceptions
        lstEventExceptions = []
        
        for exception in lstEventExceptionsCopy:
            try:
                if (bExceptionKeyProvided and (exception[EXCEPTION_KEY_FIELD_NAME].lower() == strExceptionLC)):
                    lstEventExceptions.append(exception)
                    break
                elif (bInstallKeyProvided and (exception["strInstallKey"].lower() == strInstallKeyLC)):
                    lstEventExceptions.append(exception)
                    
                    #No break because we are adding multiple exceptions in this instance
            
            except:
                pass

    #Recreation is only allowed for all exceptions, otherwise we'd have an incomplete visibility list
    elif (RECREATE_CMD_ARG_LC in dictCmdArgsIn):
        bRecreated = True
        clearEventVisibilityKVStore()

    #For faster performance, we lower case every value and then split it on the wildcard character *
    #!TFinish - OPTIONAL PERFORMANCE - We could potentially improve performance by ordering the exceptions and/or disqualifying fields in a way that eliminates/confirms events as fast as possible
    #!TFinish - OPTIONAL PERFORMANCE - We can gain ~20-40% on processing if we replace the dictionary lookup in the events with list indexing
    lstEventExceptionsPreProcessed = []
    dictLocGuidToException = {}
    
    for exception in lstEventExceptions:
        dictException = {}
        for strKey, strValue in six.iteritems(exception):
            try:
                nKey = dictExceptionFieldMap[strKey]
            except:
                #We don't add these fields because they aren't used for comparison purposes
                if (strKey in lstExceptionFieldsToIgnore):
                    continue
                else:
                    raise Exception("Unknown Exception Field: " + strKey)
                
            #We do all field comparison as strings
            strValue = str(strValue).lower()
            lstSplitValue = strValue.split("*")
            
            dictException[nKey] = lstSplitValue

        lstEventExceptionsPreProcessed.append(dictException)

        try:
            strLocGuidLC = dictException[EXCEPTION_FIELD_MAP_LOC_GUID_VALUE][0]
            del dictException[EXCEPTION_FIELD_MAP_LOC_GUID_VALUE]
        except:
            strLocGuidLC = None

        if (strLocGuidLC not in dictLocGuidToException):
            dictLocGuidToException[strLocGuidLC] = []

        dictLocGuidToException[strLocGuidLC].append(dictException)

    lstEvents = getEventsToProcessForVisibility(dictCmdArgsIn)

    bHasNonLocGuidExceptions = (None in dictLocGuidToException)
    lstVisibilityEntries = []
    for event in lstEvents:

        eventPreProcessed = {}
        
        for strKey, strValue in six.iteritems(event):
            #We do all field comparison as strings
            try:
                eventPreProcessed[int(strKey)] = str(strValue).lower()
            #If we run into an issue, we don't add the field to the pre-processed event
            except:
                pass
            
        try:
            strLocGuidLC = eventPreProcessed[EVENT_FIELD_MAP_LOC_GUID_VALUE]
        except:
            strLocGuidLC = None

        try:
            lstExceptionsToProcess = dictLocGuidToException[strLocGuidLC]
        except:
            lstExceptionsToProcess = []
    
        nVisibility = getEventVisibility(eventPreProcessed, lstExceptionsToProcess)

        #Only need to look at the non-Loc Guid exceptions if the event wasn't already detected by the exceptions above
        if (bHasNonLocGuidExceptions and (nVisibility == 0)):
            nVisibility = getEventVisibility(eventPreProcessed, dictLocGuidToException[None])

        
        if (nVisibility != 0):
            lstVisibilityEntries.append(getEventVisibilityKVStoreEntry(eventPreProcessed[EVENT_FIELD_MAP_EVENT_ID_VALUE], str(nVisibility)))

    addEventVisibilityEntriesToKVStore(lstVisibilityEntries)

    #If we have recreated the event visibility, we disable the saved search
    if (bRecreated):
        manage = Splunk_Management.SplunkManagement()
        manage.enableSavedSearch("Scheduled_Script_PerseusUMProcess_Recreate", False)
    
        
def processUnauthorizedMods(dictCmdArgsIn):
    processEventVisibility(dictCmdArgsIn)
    
if __name__ == "__main__":

    try:
        dictCmdArgs = processCommandLine()
        
        processUnauthorizedMods(dictCmdArgs)

        bLogSuccess = True
        strSuccessMessage = ""
        if (EXCEPTION_KV_STORE_KEY_CMD_ARG_LC in dictCmdArgs):
            strSuccessMessage = "ExceptionKey=" + dictCmdArgs[EXCEPTION_KV_STORE_KEY_CMD_ARG_LC] + " "
        elif (INSTALL_KV_STORE_KEY_CMD_ARG_LC in dictCmdArgs):
            strSuccessMessage = "InstallKey=" + dictCmdArgs[INSTALL_KV_STORE_KEY_CMD_ARG_LC] + " "

        if (EARLIEST_CMD_ARG_LC in dictCmdArgs):
            strSuccessMessage += ("earliest=" + dictCmdArgs[EARLIEST_CMD_ARG_LC])
        elif (INDEX_EARLIEST_CMD_ARG_LC in dictCmdArgs):
            
            #We do not log the -60m _index_earliest that runs every 5 minutes without a ExceptionKey or InstallKey 
            if (dictCmdArgs[INDEX_EARLIEST_CMD_ARG_LC] == "-60m"):
                bLogSuccess = (len(strSuccessMessage) > 0)
            
            strSuccessMessage += ("_index_earliest=" + dictCmdArgs[INDEX_EARLIEST_CMD_ARG_LC])
    
        else:
            strSuccessMessage += "All Time"

        if (bLogSuccess):
            Perseus_Management_Log.PerseusManagementLog().logProcessUnauthModsSuccess(strSuccessMessage)    

    except Exception as err:
        
        strCommandParams = ""
        try:
            if (EXCEPTION_KV_STORE_KEY_CMD_ARG_LC in dictCmdArgs):
                strCommandParams = "ExceptionKey=" + dictCmdArgs[EXCEPTION_KV_STORE_KEY_CMD_ARG_LC] + " "
            elif (INSTALL_KV_STORE_KEY_CMD_ARG_LC in dictCmdArgs):
                strCommandParams = "InstallKey=" + dictCmdArgs[INSTALL_KV_STORE_KEY_CMD_ARG_LC] + " "

            if (EARLIEST_CMD_ARG_LC in dictCmdArgs):
                strCommandParams += ("earliest=" + dictCmdArgs[EARLIEST_CMD_ARG_LC])
            elif (INDEX_EARLIEST_CMD_ARG_LC in dictCmdArgs):
                strCommandParams += ("_index_earliest=" + dictCmdArgs[INDEX_EARLIEST_CMD_ARG_LC])
            else:
                strCommandParams += "All Time"
        except:
            strCommandLine = "Unknown"
            
        Perseus_Management_Log.PerseusManagementLog().logProcessUnauthModsFailure("Process Unauthorized Modifications " + strCommandParams + " Failed with Error: " + str(err))  
