#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import Splunk_Main as SM
import Splunk_Search
import Splunk_KV_Store
import Perseus_Management_Log

import sys

HOST_INFO_FC_KV_STORE_NAME = "PerseusHostInfoFirstContact"

PERSEUS_HOST_INFO_FC_HOST_FIELD_NAME = "_key"
HOST = "host"
FIRST_REPORT_TIME = "FirstReportTime"

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

    #Even those this routine runs every few minutes, we go back at least 24 hours in case we were not running for a while
    strTimeQuery = "_index_earliest=-24h"
    
    #If time bounds are passed to the function, modify the time portion of the query 
    if (EARLIEST_CMD_ARG_LC in dictCmdArgsIn):
        strTimeQuery = "earliest=" + dictCmdArgsIn[EARLIEST_CMD_ARG_LC]
    elif (INDEX_EARLIEST_CMD_ARG_LC in dictCmdArgsIn):
        strTimeQuery = "_index_earliest=" + dictCmdArgsIn[INDEX_EARLIEST_CMD_ARG_LC]
        
    
    bAppendSearch = True
    #We rename _time to FirstReportTime in order to allow the entire result set to be batch added to the KV Store. sort +_time wasn't necessary with perseus_event but is with csv sample events (Splunk bug?)
    strSearchQuery = ('`PerseusIndex` Event.OriginInfo.ComputerName=*  ' + strTimeQuery + ' | sort +_time| dedup ' + HOST + ' sortby +_time | sort 0 -_time ' +
                      '| lookup ' + HOST_INFO_FC_KV_STORE_NAME + " " + PERSEUS_HOST_INFO_FC_HOST_FIELD_NAME + ' AS ' + HOST + ' OUTPUT ' + FIRST_REPORT_TIME + '| where isnull(' + FIRST_REPORT_TIME + ')' +
                      '| rename _time AS ' + FIRST_REPORT_TIME +
                      '| table ' + HOST + ', ' + FIRST_REPORT_TIME)

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

def clearHostInfoFirstContactKVStore():
    kvHostInfo = Splunk_KV_Store.SplunkKVStore(HOST_INFO_FC_KV_STORE_NAME)
    kvHostInfo.removeAllEntries()

def processEvents(dictCmdArgsIn):

    lstEvents = getEventsToProcess(dictCmdArgsIn)

    #We have to rename every "host" field to "_key" (we can't do this via search because Splunk doesn't return internal fields)
    for event in lstEvents:
        event[PERSEUS_HOST_INFO_FC_HOST_FIELD_NAME] = event.pop(HOST)
    
    #We batch add this to the KV Store
    kvHostInfo = Splunk_KV_Store.SplunkKVStore(HOST_INFO_FC_KV_STORE_NAME)
    kvHostInfo.addEntry(lstEvents)
        
def execute():
    try:
        dictCmdArgs = processCommandLine()
        
        processEvents(dictCmdArgs)

        #We only log success of the routine that doesn't run every 5 minutes with no parameters
        if (EARLIEST_CMD_ARG_LC in dictCmdArgs):
            Perseus_Management_Log.PerseusManagementLog().logProcessHostFirstContactSuccess("earliest=" + dictCmdArgs[EARLIEST_CMD_ARG_LC])
        elif (INDEX_EARLIEST_CMD_ARG_LC in dictCmdArgs):
            Perseus_Management_Log.PerseusManagementLog().logProcessHostFirstContactSuccess("_index_earliest=" + dictCmdArgs[INDEX_EARLIEST_CMD_ARG_LC])
        
    except Exception as err:

        strTimeQuery = ""
        try:
            dictCmdArgs = processCommandLine()
                                                                                            
            if (EARLIEST_CMD_ARG_LC in dictCmdArgs):
                strTimeQuery = " earliest=" + dictCmdArgs[EARLIEST_CMD_ARG_LC]
            elif (INDEX_EARLIEST_CMD_ARG_LC in dictCmdArgs):
                strTimeQuery = " _index_earliest=" + dictCmdArgs[INDEX_EARLIEST_CMD_ARG_LC]
        except:
            strTimeQuery = "Unknown Time"                                                                                                            
                                                                                            
        Perseus_Management_Log.PerseusManagementLog().logProcessHostFirstContactFailure("ProcessHostFirstContact" + strTimeQuery + " Failed with Error: " + str(err))  

if __name__ == "__main__":
    execute()
