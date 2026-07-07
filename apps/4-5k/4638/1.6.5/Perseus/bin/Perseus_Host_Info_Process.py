#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import six

import Splunk_Main as SM
import Splunk_Search
import Splunk_KV_Store
import Perseus_Management_Log

import sys

HOST_INFO_KV_STORE_NAME = "PerseusHostInfo"

PERSEUS_HOST_INFO_HOST_FIELD_NAME = "_key"
HOST = "host"
LAST_REPORT_TIME = "LastReportTime"
COMPUTER_NAME = "Event.OriginInfo.ComputerName"
DOMAIN_NAME = "Event.OriginInfo.DomainName"
HARDWARE_IDENTIFIER = "Event.OriginInfo.HardwareIdentifier"
EMAIL = "Event.OriginInfo.ContactEmailAddress"
OS_ARCH = "Event.OriginInfo.OSArchitecture"
OS_MAJOR = "Event.OriginInfo.OSInfo.MajorVersion"
OS_MINOR = "Event.OriginInfo.OSInfo.MinorVersion"
SP_MAJOR = "Event.OriginInfo.OSInfo.SPMajorVersion"
SP_MINOR = "Event.OriginInfo.OSInfo.SPMinorVersion"
AGENT_VERSION = "Event.OriginInfo.PerseusAgentVersion"
REPORTER_VERSION = "Event.OriginInfo.PerseusReporterVersion"
IPV4_IP_ADDRESS = "Event.OriginInfo.IPV4IpAddress"
PUBLIC_IP_ADDRESS = "Event.OriginInfo.PublicIpAddress"

ALL_HOST_INFO_FIELDS_LIST = [ HOST.split(".")[-1], LAST_REPORT_TIME.split(".")[-1], COMPUTER_NAME.split(".")[-1], DOMAIN_NAME.split(".")[-1], HARDWARE_IDENTIFIER.split(".")[-1], EMAIL.split(".")[-1], OS_MAJOR.split(".")[-1], OS_MINOR.split(".")[-1], SP_MAJOR.split(".")[-1], SP_MINOR.split(".")[-1], AGENT_VERSION.split(".")[-1], REPORTER_VERSION.split(".")[-1], IPV4_IP_ADDRESS.split(".")[-1], PUBLIC_IP_ADDRESS.split(".")[-1]]

EARLIEST_CMD_ARG_LC = "-earliest"
INDEX_EARLIEST_CMD_ARG_LC = "-index_earliest"

def processCommandLine():

    dictCommandLine = {}

    for nArg in range(1, len(sys.argv)):
        strArgLC = sys.argv[nArg].lower()
        
        #Single value argument
        if ((strArgLC == EARLIEST_CMD_ARG_LC) or (strArgLC == INDEX_EARLIEST_CMD_ARG_LC)):
            nArg += 1
            dictCommandLine[strArgLC] = sys.argv[nArg]

    return dictCommandLine

def getEventsToProcess(dictCmdArgsIn):

    strTimeQuery = ""
    
    #If time bounds are passed to the function, modify the time portion of the query 
    if (EARLIEST_CMD_ARG_LC in dictCmdArgsIn):
        strTimeQuery = "earliest=" + dictCmdArgsIn[EARLIEST_CMD_ARG_LC]
    elif (INDEX_EARLIEST_CMD_ARG_LC in dictCmdArgsIn):
        strTimeQuery = "_index_earliest=" + dictCmdArgsIn[INDEX_EARLIEST_CMD_ARG_LC]

    bAppendSearch = True
    #We do not dedup here because we want every event. If an OriginInfo event doesn't have every field, we use previous events to the find the last time it did
    strRootSearchQuery = '`PerseusIndex` "<OriginInfo>"'
    strSearchQuery = (strRootSearchQuery + " " + strTimeQuery + " " +
                      "| rename _time as " + LAST_REPORT_TIME + 
                      "| eval " + COMPUTER_NAME + " = COALESCE('" + COMPUTER_NAME + "', " + HOST + ") " +
                      '| table ' + HOST +
                      ", " + LAST_REPORT_TIME + 
                      ", " + COMPUTER_NAME +
                      ", " + DOMAIN_NAME +
                      ", " + HARDWARE_IDENTIFIER +
                      ", " + EMAIL +
                      ", " + OS_ARCH +
                      ", " + OS_MAJOR +
                      ", " + OS_MINOR +
                      ", " + SP_MAJOR +
                      ", " + SP_MINOR +
                      ", " + AGENT_VERSION +
                      ", " + REPORTER_VERSION +
                      ", " + IPV4_IP_ADDRESS +
                      ", " + PUBLIC_IP_ADDRESS)

    #Handle Perseus Demo which doesn't have full events and requires prepending with | and modifying the time query
    if (SM.IS_PERSEUS_DEMO):
        bAppendSearch = False
        strSearchQuery = strSearchQuery.replace(strRootSearchQuery, " | `PerseusIndex` Event.OriginInfo.ComputerName=*")

        nEqualIndex = strTimeQuery.find("=")
        if (nEqualIndex != -1):
            strNewTimeQuery = "_time >" + strTimeQuery[nEqualIndex:] + " "
            strSearchQuery = strSearchQuery.replace(strTimeQuery, strNewTimeQuery)

    query = Splunk_Search.SplunkSearchQuery(strSearchQuery, bAppendSearch)
    jsonResults = query.executeQueryAndGetJsonResults()        
    
    return jsonResults

def processEvents(dictCmdArgsIn):
    lstEvents = getEventsToProcess(dictCmdArgsIn)
    dictHostInfo = {}

    #Most recent events are returned first, so we use the most recent value for each field to populate the KV Store
    for event in lstEvents:
        #We lower case this for lookup case sensitivity
        event[HOST] = event[HOST].lower()
        strHost = event[HOST]
        
        if (strHost not in dictHostInfo):
            dictHostInfo[strHost] = {}
            
        for strField, strValue in six.iteritems(event):
            #Cannot use dot notation in KV Store Field Names, so we use only the part of the field name coming after the final '.'
            strField = strField.split(".")[-1]

            #We have to rename this field to _key since the host guid is the key for PerseusHostInfo
            if (strField == HOST):
                strField = PERSEUS_HOST_INFO_HOST_FIELD_NAME
                
            if (len(strValue) > 0):
                if (strField not in dictHostInfo[strHost]):
                    dictHostInfo[strHost][strField] = strValue

    kvHostInfo = Splunk_KV_Store.SplunkKVStore(HOST_INFO_KV_STORE_NAME)
    lstAllHostEntriesIn = kvHostInfo.getEntries()
    dictHostsToEntries = {}
    for entry in lstAllHostEntriesIn:
        dictHostsToEntries[entry[PERSEUS_HOST_INFO_HOST_FIELD_NAME]] = entry

    lstEntriesToAdd = []
    for strHost, dictCurrentHostInfo in six.iteritems(dictHostInfo):
        if (not updateHostInfoInKVStore(dictCurrentHostInfo, dictHostsToEntries)):
            lstEntriesToAdd.append(dictCurrentHostInfo)

    #!TFinish - OPTIONAL - We may at some point want to populate unpopulated values for search purposes
    kvHostInfo.addEntry(lstEntriesToAdd)
        
#!TFinish - OPTIONAL - Make this generic and add it to Splunk_KV_Store
#Returns False if the host does not exist, indicating it should be added by caller
def updateHostInfoInKVStore(dictHostInfoIn, dictHostsToEntriesIn):
    #We let errors pass through. If future changes to the code result in expected intermittent failures, we should skip the individual errors to process the other hosts and then log what failed
    
    #!TFinish - OPTIONAL PERFORMANCE - Can we optimize this by getting all the hosts first in a single KV store call, then batch add/update?
    strHost = dictHostInfoIn[PERSEUS_HOST_INFO_HOST_FIELD_NAME]
    #Hosts are case sensitive, so we don't have to do any manipulation here
    if (strHost not in dictHostsToEntriesIn):
        return False
       
    #Merges the two together, using the passed in field values for any overlapping fields
    entryToUpdate = dictHostsToEntriesIn[strHost]
    entryToUpdate.update(dictHostInfoIn)
    kvHostInfo = Splunk_KV_Store.SplunkKVStore(HOST_INFO_KV_STORE_NAME)
    kvHostInfo.updateEntry(entryToUpdate)

    return True

def clearHostInfoKVStore():
    kvHostInfo = Splunk_KV_Store.SplunkKVStore(HOST_INFO_KV_STORE_NAME)
    kvHostInfo.removeAllEntries()

def execute():
    try:

        dictCmdArgs = processCommandLine()
        
        processEvents(dictCmdArgs)

        if (EARLIEST_CMD_ARG_LC in dictCmdArgs):
            Perseus_Management_Log.PerseusManagementLog().logProcessHostInfoSuccess("earliest=" + dictCmdArgs[EARLIEST_CMD_ARG_LC])
        elif (INDEX_EARLIEST_CMD_ARG_LC in dictCmdArgs):
            #We do not log the -60m _index_earliest that runs every 5 minutes
            if (dictCmdArgs[INDEX_EARLIEST_CMD_ARG_LC] != "-60m"):
                Perseus_Management_Log.PerseusManagementLog().logProcessHostInfoSuccess("_index_earliest=" + dictCmdArgs[INDEX_EARLIEST_CMD_ARG_LC])
        else:
            Perseus_Management_Log.PerseusManagementLog().logProcessHostInfoSuccess("All Time")
        
    except Exception as err:

        strTimeQuery = ""
        try:
            dictCmdArgs = processCommandLine()
                                                                                            
            if (EARLIEST_CMD_ARG_LC in dictCmdArgs):
                strTimeQuery = " earliest=" + dictCmdArgs[EARLIEST_CMD_ARG_LC]
            elif (INDEX_EARLIEST_CMD_ARG_LC in dictCmdArgs):
                strTimeQuery = " _index_earliest=" + dictCmdArgs[INDEX_EARLIEST_CMD_ARG_LC]
            else:
                strTimeQuery = " All Time"
        except:
            strTimeQuery = "Unknown Time"
            
        Perseus_Management_Log.PerseusManagementLog().logProcessHostInfoFailure("Process Host Info" + strTimeQuery + " Failed with Error: " + str(err))  

if __name__ == "__main__":
    execute()
