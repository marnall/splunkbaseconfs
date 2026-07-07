#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import Splunk_Main
import Splunk_KV_Store
import Splunk_Search

import Perseus_Management_Log

import sys
import time
import json

CACHE_TYPE_CMD_ARG_LC = "-type"
SPLUNK_USER_CMD_ARG_LC = "-user"
HOST_GUID_CMD_ARG_LC = "-host"

CACHE_NOT_AVAILABLE = "0"
CACHE_AVAILABLE = "1"

CACHE_INFO_TYPE_FIELD_NAME = "strCacheType"
CACHE_INFO_TYPE_RECOLLECTION = "Recollection"

CACHE_INFO_SPLUNK_USER_FIELD_NAME = "strSplunkUser"
CACHE_INFO_HOST_GUID_FIELD_NAME = "strHostGuid"

CACHE_INFO_LATEST_INDEX_TIME_FIELD_NAME = "dtLatestIndexTime"
CACHE_INFO_CREATION_TIME_FIELD_NAME = "dtCreationTime"
CACHE_INFO_UPDATED_TIME_FIELD_NAME = "dtUpdatedTime"
CACHE_INFO_LATEST_ACCESS_TIME_FIELD_NAME = "dtLatestAccessTime"

#NOTE: If we change this, update RECOLLECTION_EVENTS_CACHE_RENAME_COMMAND and the Perseus Demo SaaS Engine
RECOLLECTION_EVENTS_CACHE_FIELD_LIST = "host, time, Event_ID, Event_LocMod_LocModType, Event_LocMod_Location_LocGuid, Event_LocMod_Location_LocUser, Event_LocMod_LocEntry_EntryType, Event_LocMod_LocEntry_EntryName, Event_LocMod_LocEntry_EntryData, Event_LocMod_LocEntry_AutoExecFiles_AutoExecFile_AEFRawString, Event_LocMod_LocEntry_AutoExecFiles_AutoExecFile_AEFAttributes_AEFAttribute_AEFAttrMD5, Event_LocMod_ForensicMod_ForensicSource, Event_LocMod_ForensicMod_ForensicModType, Event_LocMod_ForensicMod_ExactFMTime, Event_LocMod_ForensicMod_EarliestFMTime, Event_LocMod_ForensicMod_LatestFMTime, Event_LocMod_ForensicMod_FirstEvent, Event_LocMod_ForensicMod_ForensicDescription"
#Use getRecollectionToCacheRenameFieldsCommand() to generate
RECOLLECTION_EVENTS_CACHE_RENAME_COMMAND = "rename Event.ID AS Event_ID, Event.LocMod.LocModType AS Event_LocMod_LocModType, Event.LocMod.Location.LocGuid AS Event_LocMod_Location_LocGuid, Event.LocMod.Location.LocUser AS Event_LocMod_Location_LocUser, Event.LocMod.LocEntry.EntryType AS Event_LocMod_LocEntry_EntryType, Event.LocMod.LocEntry.EntryName AS Event_LocMod_LocEntry_EntryName, Event.LocMod.LocEntry.EntryData AS Event_LocMod_LocEntry_EntryData, Event.LocMod.LocEntry.AutoExecFiles.AutoExecFile.AEFRawString AS Event_LocMod_LocEntry_AutoExecFiles_AutoExecFile_AEFRawString, Event.LocMod.LocEntry.AutoExecFiles.AutoExecFile.AEFAttributes.AEFAttribute.AEFAttrMD5 AS Event_LocMod_LocEntry_AutoExecFiles_AutoExecFile_AEFAttributes_AEFAttribute_AEFAttrMD5, Event.LocMod.ForensicMod.ForensicSource AS Event_LocMod_ForensicMod_ForensicSource, Event.LocMod.ForensicMod.ForensicModType AS Event_LocMod_ForensicMod_ForensicModType, Event.LocMod.ForensicMod.ExactFMTime AS Event_LocMod_ForensicMod_ExactFMTime, Event.LocMod.ForensicMod.EarliestFMTime AS Event_LocMod_ForensicMod_EarliestFMTime, Event.LocMod.ForensicMod.LatestFMTime AS Event_LocMod_ForensicMod_LatestFMTime, Event.LocMod.ForensicMod.FirstEvent AS Event_LocMod_ForensicMod_FirstEvent, Event.LocMod.ForensicMod.ForensicDescription AS Event_LocMod_ForensicMod_ForensicDescription"

def processCommandLine():

     dictCommandLine = {}

     for nArg in range(1, len(sys.argv)):
          strArgLC = sys.argv[nArg].lower()

          #Single value argument
          if ((strArgLC == CACHE_TYPE_CMD_ARG_LC) or (strArgLC == SPLUNK_USER_CMD_ARG_LC) or (strArgLC == HOST_GUID_CMD_ARG_LC)):
               nArg += 1
               dictCommandLine[strArgLC] = sys.argv[nArg]

     #Default Arguments
     if (SPLUNK_USER_CMD_ARG_LC not in dictCommandLine):
          dictCommandLine[SPLUNK_USER_CMD_ARG_LC] = None
               
     return dictCommandLine

def getRecollectionEventFieldList():
     return RECOLLECTION_EVENTS_CACHE_FIELD_LIST.replace(" _", " __").replace("_", ".").replace(" ..", " _")

def getRecollectionFieldNameFromCacheFieldName(strFieldIn):

     #NOTE: If we change this, update RECOLLECTION_EVENTS_CACHE_RENAME_COMMAND and the Perseus Demo SaaS Engine

     #We return any built-in field names as is
     if (strFieldIn[0] == "_"):
          return strFieldIn
    
     return strFieldIn.replace("_", ".")

#Maps the fields in the perseus index to the fields in the KV Store
def getRecollectionToCacheRenameFieldsCommand():
     strCommand = ""

     for strField in RECOLLECTION_EVENTS_CACHE_FIELD_LIST.replace(", ", ",").split(","):

          #NOTE: If we change this, update RECOLLECTION_EVENTS_CACHE_RENAME_COMMAND and the Perseus Demo SaaS Engine

          strFieldReplaced = getRecollectionFieldNameFromCacheFieldName(strField)
          
          if (strField == strFieldReplaced):
               continue

          if (strCommand):
               strCommand += ", "
               
          strCommand += (strFieldReplaced + " AS " + strField)

     return ("rename " + strCommand)

#Maps the fields in the KV Store to the fields in the perseus index
def getRecollectionCacheRenameFieldsCommand():
     strCommand = ""

     for strField in RECOLLECTION_EVENTS_CACHE_FIELD_LIST.replace(", ", ",").split(","):

          strFieldReplaced = getRecollectionFieldNameFromCacheFieldName(strField)

          if (strField == strFieldReplaced):
               if (strField == "time"):
                   strFieldReplaced =  "_time"
               else:    
                    continue

          if (strCommand):
               strCommand += ", "
               
          strCommand += (strField + " AS " + strFieldReplaced)

     return ("rename " + strCommand)

class PerseusCacheInfo(Splunk_KV_Store.SplunkKVStore):

     def __init__(self, headerIn = None, splunkServerIn = Splunk_Main.splunkServerDefault, strAppContextIn = None, strAppContextUserIn = None):

          self.strKVStoreName = "PerseusCacheInfo"
          self.header = headerIn
          self.splunkServer = splunkServerIn
          self.strAppContext = strAppContextIn
          self.strAppContextUser = strAppContextUserIn

     def createNewCacheInfoEntry(self, strCacheTypeIn, strSplunkUserIn, strHostGuidIn, nLatestIndexUnixTimeIn):
     
          nUnixTimeNow = time.time()

          self.addEntry({  CACHE_INFO_TYPE_FIELD_NAME : strCacheTypeIn,
                           CACHE_INFO_SPLUNK_USER_FIELD_NAME : strSplunkUserIn,
                           CACHE_INFO_HOST_GUID_FIELD_NAME : strHostGuidIn,
                           CACHE_INFO_LATEST_INDEX_TIME_FIELD_NAME : nLatestIndexUnixTimeIn,
                           CACHE_INFO_CREATION_TIME_FIELD_NAME : nUnixTimeNow,
                           CACHE_INFO_UPDATED_TIME_FIELD_NAME : nUnixTimeNow,
                           CACHE_INFO_LATEST_ACCESS_TIME_FIELD_NAME : nUnixTimeNow            
                           })
                                 
     def updateCacheInfoEntry(self, entryIn, nLatestIndexUnixTimeIn):

          nUnixTimeNow = time.time()

          entryIn[CACHE_INFO_LATEST_ACCESS_TIME_FIELD_NAME] = nUnixTimeNow
          
          #Only updated if additional events were cached
          if (entryIn[CACHE_INFO_LATEST_INDEX_TIME_FIELD_NAME] != nLatestIndexUnixTimeIn):
               entryIn[CACHE_INFO_UPDATED_TIME_FIELD_NAME] = nUnixTimeNow

          self.updateEntry(entryIn)
          
     def createOrUpdateCacheInfoEntry(self, entryIn, strCacheTypeIn, strSplunkUserIn, strHostGuidIn, nLatestIndexUnixTimeIn):

          if (entryIn is None):
               self.createNewCacheInfoEntry(strCacheTypeIn, strSplunkUserIn, strHostGuidIn, nLatestIndexUnixTimeIn)
          else:
               self.updateCacheInfoEntry(entryIn, nLatestIndexUnixTimeIn)          
                                      
     def getCacheInfoEntry(self, strCacheTypeIn, strSplunkUserIn, strHostGuidIn):          
          return self.searchEntries({ CACHE_INFO_TYPE_FIELD_NAME : strCacheTypeIn, CACHE_INFO_SPLUNK_USER_FIELD_NAME : strSplunkUserIn,  CACHE_INFO_HOST_GUID_FIELD_NAME : strHostGuidIn })
          
class RecollectionModsCache(Splunk_KV_Store.SplunkKVStore):

     def __init__(self, headerIn = None, splunkServerIn = Splunk_Main.splunkServerDefault, strAppContextIn = None, strAppContextUserIn = None):

          self.strKVStoreName = "PerseusRecollectionEventsCache"
          self.header = headerIn
          self.splunkServer = splunkServerIn
          self.strAppContext = strAppContextIn
          self.strAppContextUser = strAppContextUserIn
          self.kvCacheInfo = PerseusCacheInfo(self.header)

     #We Let Errors Pass Through Which Will Make Page Default to Not Using the Cache
     def createCacheForHost(self, strSplunkUserIn, strHostGuidIn, jsonEventsIn = None):
          
          #We append Event.LocMod.ForensicMod.EarliestFMTime to the table returned by PerseusGetRecollectionMods. But if in the future PerseusGetRecollectionForensicMods

          entryCacheInfo = self.kvCacheInfo.getCacheInfoEntry(CACHE_INFO_TYPE_RECOLLECTION, strSplunkUserIn, strHostGuidIn)

          #We'll let Perseus Health detect multiple matching Cache Info entries
          nLatestIndexUnixTime = None
          if (len(entryCacheInfo) > 0):
               entryCacheInfo = entryCacheInfo[0]
               #Let Errors Get Out To Default to No Caching if Info Entry is not as Expected
               nLatestIndexUnixTime = entryCacheInfo[CACHE_INFO_LATEST_INDEX_TIME_FIELD_NAME]
          else:
               entryCacheInfo = None
               
          strIndexTimeQuery = ""
          if (nLatestIndexUnixTime is not None):
               strIndexTimeQuery = " | search _indextime > " + str(nLatestIndexUnixTime)

          LATEST_INDEX_TIME = "latestIndexTime" 
          strQuery = "`PerseusGetRecollectionMods(PerseusRecollectionBaseSearch, " + strHostGuidIn + ", )`, Event.LocMod.ForensicMod.EarliestFMTime " + strIndexTimeQuery + " | eval time = _time | eventstats max(_indextime) as " + LATEST_INDEX_TIME + " | " + RECOLLECTION_EVENTS_CACHE_RENAME_COMMAND + " | table " + RECOLLECTION_EVENTS_CACHE_FIELD_LIST + ", " + LATEST_INDEX_TIME

          #This is the common situation where we are caching from events that have been indexed
          if (jsonEventsIn is None):
               
               query = Splunk_Search.SplunkSearchQuery(strQuery)
               jsonEvents = query.executeQueryAndGetJsonResults()

               if (len(jsonEvents)):

                    #Update this to the new latest index time
                    nLatestIndexUnixTime = jsonEvents[0][LATEST_INDEX_TIME]

                    #Remove the Index Time Field Before Adding it to the KV Store
                    for nEntry in range(0, len(jsonEvents)):
                         jsonEvents[nEntry].pop(LATEST_INDEX_TIME, None)
                         
                    self.addEntry(jsonEvents)
               #else: Leave nLatestIndexUnixTime the same since no new events were detected
                    
          #This is a use-case where events are explicitly passed to the script to load into the cache. This supports the Perseus Demo Recollection Dashboard with Customer Data use-case. In the future, it may be used to reduce indexing demands by indexing some Recollection events only on demand 
          else:               
               self.addEntry(jsonEventsIn)
               nLatestIndexUnixTime = 0
     
          #We do NOT add/update the info entry unless we got to this point
          #There's a small chance we end up with a corrupted state if we can't add the entry info at this point. But we'll let Perseus Health detect and resolve this
          try:
               self.kvCacheInfo.createOrUpdateCacheInfoEntry(entryCacheInfo, CACHE_INFO_TYPE_RECOLLECTION, strSplunkUserIn, strHostGuidIn, nLatestIndexUnixTime)
               
          #We don't throw an error, we still return to use the cache (since it shoudl be populated), but we log it
          except Exception as err:
               strUserError = ""
               if (strSplunkUserIn):
                    strUserError = "for User " + strSplunkUserIn
               
               strError = "Cache Info Create/Update for " + CACHE_INFO_TYPE_RECOLLECTION + " Cache " + strUserError + "for " + strHostGuidIn + " Failed with Error: " + str(err)
               #We explicitly pass the header because this can be called from the Perseus Demo where credentials are not available except through pass through
               Perseus_Management_Log.PerseusManagementLog(self.header).logRecollectionCacheHostSuccess(strError)               
          
          #If we get here (didn't encounter errors in retrieving Cache Info or the PerseusGetRecollectionMods), then we have cache data to use
          return True

     def createCacheForHostFromJsonEventsString(self, strSplunkUserIn, strHostGuidIn, strEventsJsonIn):

          try:
               
               jsonEvents = json.loads(strEventsJsonIn)
               
          except Exception as err:
               raise Exception("Count Not Convert Json Events String to Json (" + str(err) + ")")


          #We Let Errors Pass Through
          return self.createCacheForHost(strSplunkUserIn, strHostGuidIn, jsonEvents)
      
if __name__ == "__main__":


     strCacheType = "Unspecified"
     strSplunkUser = None
     strHostGuid = "Unspecified"

     try:
          dictCmdArgs = processCommandLine()          
          
          strCacheType = dictCmdArgs[CACHE_TYPE_CMD_ARG_LC]
          strSplunkUser = dictCmdArgs[SPLUNK_USER_CMD_ARG_LC]
          strHostGuid = dictCmdArgs[HOST_GUID_CMD_ARG_LC]

          if (strCacheType == CACHE_INFO_TYPE_RECOLLECTION):
               kvCache = RecollectionModsCache()
               bCacheAvailable = kvCache.createCacheForHost(strSplunkUser, strHostGuid)

          else:
               raise Exception(strCacheType + " Is Not a Valid Cache Type")
          
          print("Status")
          
          if (bCacheAvailable):
               print(CACHE_AVAILABLE)
          else:
               print(CACHE_NOT_AVAILABLE)
               
          #We don't log success

     except Exception as err:

          strUserError = ""
          if (strSplunkUser):
               strUserError = "for User " + strSplunkUser
               
          strError = "Get " + strCacheType + " Cache " + strUserError + "for " + strHostGuid + " Failed with Error: " + str(err)
          
          print("Error Message")
          print (strError)
        
          Perseus_Management_Log.PerseusManagementLog().logRecollectionCacheHostFailure(strError)
