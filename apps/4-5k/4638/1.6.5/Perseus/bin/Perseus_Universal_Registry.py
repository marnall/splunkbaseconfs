#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import six

import Splunk_Main
import Splunk_Search
import Splunk_KV_Store

import Perseus_Management_Log

from collections import defaultdict

#!TFinish - OPTIONAL - Detect incomplete snapshot by noting snapshot does not have dtSnapshotEndTime
#!TFinish - OPTIONAL - PerseusUniversalRegistrySnapshotPresentationData and PerseusUniversalRegistrySnapshotPresentationKeyToEventsPrep are essentially temporary stores. Add an option to delete these KV stores and reclaim disk space (see: https://answers.splunk.com/answers/613389/kvstore-mongodb-compact-command.html)
#!TFinish - OPTIONAL - If an entry is marked as Blocked, REMOVE it from the snapshot for that system
#!TFinish - OPTIONAL - Compress the Json data for faster download and smaller KV store usage

PERSEUS_UREG_SNAPSHOT_RAW_KV_STORE_NAME = "PerseusUniversalRegistrySnapshotRawData"
PERSEUS_UREG_SNAPSHOT_INFO_KV_STORE_NAME = "PerseusUniversalRegistrySnapshotInfo"
PERSEUS_UREG_SNAPSHOT_PRESENTATION_DATA_KV_STORE_NAME = "PerseusUniversalRegistrySnapshotPresentationData"
PERSEUS_UREG_SNAPSHOT_PRESENTATION_KEY_TO_EVENTS_KV_STORE_NAME = "PerseusUniversalRegistrySnapshotPresentationKeyToEventsLookup"
PERSEUS_UREG_SNAPSHOT_PRESENTATION_JSON_KV_STORE_NAME = "PerseusUniversalRegistrySnapshotPresentationJson"
PERSEUS_UREG_SNAPSHOT_ID_FIELD_NAME = "nSnapshotID"

PERSEUS_UREG_PATH_FIELD_NAME = "strPath"
PERSEUS_UREG_OBJECT_NAME_FIELD_NAME = "strObjectName"

PERSEUS_UREG_OBJECT_TYPE_FIELD_NAME = "strObjectType"
PERSEUS_UREG_OBJECT_TYPE_REG_VALUE = "1"
PERSEUS_UREG_OBJECT_TYPE_REG_KEY = "2"
PERSEUS_UREG_OBJECT_TYPE_REG_VALUE_DATA = "3"

PERSEUS_UREG_REP_FIELD_NAME = "nRep"
PERSEUS_UREG_REP_KNOWN_GOOD_VALUE = "-1"

PERSEUS_UREG_HOSTS_WITH_NAME_FIELD_NAME = "nHostsWithObjectName"

PERSEUS_UREG_OBJECT_TYPE_JSON_FIELD_NAME = "Type"
PERSEUS_UREG_HOSTS_WITHNAME_JSON_FIELD_NAME = "WithName"

PERSEUS_UREG_PRESENTATION_JSON_FIELD_NAME = "strJson"

class UniversalRegException(Exception):
    pass

def createNewUniversalRegSnapshot():

    try:
        query = Splunk_Search.SplunkSearchQuery(" | `PerseusUniversalRegGetLastSnapshotInfo`", False)
        #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
        jsonResults = query.executeQueryAndGetJsonResults()

        strNewSnapshotIDOut = str(int(jsonResults[0]["SnapshotID"]) + 1)
        strEarliestIndexTime = jsonResults[0]["SnapshotStartTime"]

    except:
        raise UniversalRegException("Previous Snapshot Info could not be retrieved. If this issue persists, please contact support@PerseusSec.com.")
    
    strQuery = '`PerseusUniversalRegCreateSnapshotFromIndex(' + strNewSnapshotIDOut + ', ' + strEarliestIndexTime + ')`'

    dtSnapshotStartTime = Splunk_Main.getSplunkTimeForNow()
    
    query = Splunk_Search.SplunkSearchQuery(strQuery)
    #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
    jsonResults = query.executeQueryAndGetJsonResults()

    if (len(jsonResults) == 0):
        return None
    
    dtSnapshotEndTime = Splunk_Main.getSplunkTimeForNow()
    
    #Create Snapshot Info Entry
    strQuery = '| `PerseusUniversalRegCreateSnapshotInfo(' + strNewSnapshotIDOut + ', ' + str(dtSnapshotStartTime) + ', ' + str(dtSnapshotEndTime) + ')`'
    
    query = Splunk_Search.SplunkSearchQuery(strQuery, False)
    #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
    query.executeQueryAndGetJsonResults()

    return strNewSnapshotIDOut

def createPresentationForUniversalRegSnapshot(strSnapshotIDIn):

    strQuery = '| `PerseusUniversalRegCreateSnapshotPresentation(' + strSnapshotIDIn + ')`'

    query = Splunk_Search.SplunkSearchQuery(strQuery, False)
    #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
    query.executeQueryAndGetJsonResults()

def createPresentationKeyToEventsForUniversalRegSnapshot(strSnapshotIDIn):

    #Prepare the Temporary Lookup
    strQuery = '| `PerseusUniversalRegCreateSnapshotPresentationKeyToEventsPrep(' + strSnapshotIDIn + ')`'

    query = Splunk_Search.SplunkSearchQuery(strQuery, False)
    #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
    query.executeQueryAndGetJsonResults()

    #Add the Key to Events Entries
    strQuery = '| `PerseusUniversalRegAddSnapshotPresentationKeyEvents(' + strSnapshotIDIn + ')`'

    query = Splunk_Search.SplunkSearchQuery(strQuery, False)
    #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
    query.executeQueryAndGetJsonResults()

class recursivedefaultdict(defaultdict):
    def __init__(self):
        self.default_factory = type(self)
        
#Call this function by splitting the path
def addPresentationEntryToRdd(itPathIn, entryDictIn, rddIn):
    try:
        addPresentationEntryToRdd(itPathIn, entryDictIn, rddIn[six.next(itPathIn)])
    #The node is reached when we hit Stop Iteration - we store the relevant entry data in the node
    except StopIteration:
        rddIn[Splunk_KV_Store.SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME] = entryDictIn[Splunk_KV_Store.SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME]
        rddIn[PERSEUS_UREG_OBJECT_TYPE_JSON_FIELD_NAME] = entryDictIn[PERSEUS_UREG_OBJECT_TYPE_FIELD_NAME]
        rddIn[PERSEUS_UREG_REP_FIELD_NAME] = entryDictIn[PERSEUS_UREG_REP_FIELD_NAME]
        rddIn[PERSEUS_UREG_HOSTS_WITHNAME_JSON_FIELD_NAME] = entryDictIn[PERSEUS_UREG_HOSTS_WITH_NAME_FIELD_NAME]

#!TFinish - OPTIONAL - This function could probably be optimizated (removing the sort for instance still works and gives about a 5% performance boost). However, this function takes less than 1% of the total snapshot time, so optimizing is not likely to signficantly impact snapshot performance unless we dramatically improve the other areas
#!TFinish - OPTIONAL - Test the corner case where a quote is contained in a subkey that is a parent of a node. It is unlikely we'll run into this in realistic situations, but we should handle it just in case
def getPresentationJsonStringFromDictionaryRecurse(rddAllPathsIn, strKeyIn = None):

    if (strKeyIn is None):
        strJsonString = ""
    else:
        #We store with shorter name to decrease size of the json transfer
        strJsonString = '{"t":"%s",' % (strKeyIn.replace('"', '\\"'))

    strChildData = ""
    bChildDataIsFolder = False
    strChildContains = ""

    for strChildKey in sorted(rddAllPathsIn.keys()):
         
        child = rddAllPathsIn[strChildKey]
                        
        if (isinstance(child, recursivedefaultdict)):
            if (len(strChildContains) == 0):
                #The first call to this function is not for a valid key, so we don't write out anything other than its children
                if (strKeyIn is not None):
                    #We store with shorter names/value to decrease size of the json transfer (1 is used for folder because its presence is enough to indicate it is a folder)
                    strChildContains = '"f":1,"c":['
            #Avoid double appending comma                           
            elif (not strChildContains.endswith(",")):
                strChildContains += ","

            strChildContains += getPresentationJsonStringFromDictionaryRecurse(child, strChildKey)

        else:

            #Avoid double appending comma or appending to previously empty string                           
            if ((len(strChildData) > 0) and (not strChildData.endswith(","))):
                strChildData += ","

            if (strChildKey == PERSEUS_UREG_REP_FIELD_NAME):
                #Since most files should be known good, we save space in the json by not adding the field
                if (child != PERSEUS_UREG_REP_KNOWN_GOOD_VALUE):
                    strChildData += ('"r":' + str(child))

            elif ((strChildKey == PERSEUS_UREG_OBJECT_TYPE_JSON_FIELD_NAME) and (child == PERSEUS_UREG_OBJECT_TYPE_REG_KEY)):
               #We flag this instead of setting it now because if one of the children is a recursivedefaultdict, folder is set there
               bChildDataIsFolder = True
                    
            elif (strChildKey == PERSEUS_UREG_HOSTS_WITHNAME_JSON_FIELD_NAME):
                #We store with shorter names/value to decrease size of the json transfer
                strChildData += ('"w":' + str(child))
                                    
            #We expose this for faster retrieval of events associated with the entry
            elif (strChildKey == Splunk_KV_Store.SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME):
                strChildData += ('"k":"' + child + '"')

            #NOTE: Any new Fields must be added to addPresentationEntryToRdd

    if (strChildContains[-1:] == ","):
        strChildContains = strChildContains[:-1]

    #The first call to this function is not for a valid key, so we don't write out anything other than its children
    if ((strKeyIn is not None) and (len(strChildContains) > 0)):
        strChildContains += "]"
        if (len(strChildData) > 0):
            strChildContains += ","

    strJsonString += strChildContains 

    if (strChildData[-1:] == ","):
        strChildData = strChildData[:-1]

    #If the child doesn't contain any sub-elements, we flag it as a folder if necessary
    #Technically this would break if the bChildDataIsFolder was true and there were no other data elements. This would be a code mistake though
    if (bChildDataIsFolder and (len(strChildContains) == 0)):
        #We store with shorter names/value to decrease size of the json transfer (1 is used for folder because its presence is enough to indicate it is a folder)
        strChildData += ',"f":1'

    #The first call to this function is not for a valid key, so we don't write out anything other than its children
    if (strKeyIn is not None):
        strJsonString += strChildData + "}"

    return strJsonString

def getPresentationJsonStringFromDictionary(rddAllPathsIn):

    strJsonString = getPresentationJsonStringFromDictionaryRecurse(rddAllPathsIn)
    #String is already json escaped for " by getPresentationJsonStringFromDictionaryRecurse. Backslash was replaced with a tab (which was done to keep the recursive function from splitting child nodes that \ in their name). Replace | with escaped \ here. NOTE: No tab should appear anywhere in the json because | cannot be in a registry key name or value name
    strJsonString = strJsonString.replace("\t", "\\\\")

    #Must wrap whole JSON in []
    strJsonString = ("[" + strJsonString + "]")

    return strJsonString

def createJsonForPresentationAndAddToKVStore(strSnapshotIDIn):

    kvPresentation = Splunk_KV_Store.SplunkKVStore(PERSEUS_UREG_SNAPSHOT_PRESENTATION_DATA_KV_STORE_NAME)
    #strSnapshotIDIn must be converted to an int to return proper results
    lstEntries = kvPresentation.getEntriesNoMax({ PERSEUS_UREG_SNAPSHOT_ID_FIELD_NAME : int(strSnapshotIDIn) })
    
    n = 0
    setAllPaths = set()
    dictAllPaths = {}
 
    rddAllPaths = recursivedefaultdict()
    for entry in lstEntries:
        #!TFinish - OPTIONAL - If we want to create a (optional?) slimmer version of the UReg if we expand beyond the auto-execs only, these can create a lot of entries but provide less value:
##        if ((entry[PERSEUS_UREG_PATH_FIELD_NAME].endswith("\\domains")) or
##            (entry[PERSEUS_UREG_PATH_FIELD_NAME].endswith("\\clsid")) or
##            (entry[PERSEUS_UREG_PATH_FIELD_NAME].endswith("\\classes")) or
##            (entry[PERSEUS_UREG_PATH_FIELD_NAME].endswith("\\activex compatibility")) or
##            (entry[PERSEUS_UREG_PATH_FIELD_NAME].endswith("\\services")) or
##            (entry[PERSEUS_UREG_PATH_FIELD_NAME].endswith("\\control\\class")) or
##            (entry[PERSEUS_UREG_PATH_FIELD_NAME].endswith("\\appid")) or
##            (entry[PERSEUS_UREG_PATH_FIELD_NAME].endswith("\\app paths")) or
##            (entry[PERSEUS_UREG_PATH_FIELD_NAME].endswith("\\shell extensions\\approved")) or
##            (entry[PERSEUS_UREG_PATH_FIELD_NAME].endswith("\\shareddlls"))):
##
##            continue

        #We replace \ in the Entry Name with a | so that it won't be recursed as though it is a path below. No tab should appear anywhere in the Entry Name because tab cannot be in a registry key name or value name
        strFullPath = entry[PERSEUS_UREG_PATH_FIELD_NAME] + "\\" + entry[PERSEUS_UREG_OBJECT_NAME_FIELD_NAME].replace("\\", "\t")

        #We only need to escape " and \ because all other json escape values are for whitespace characters. " is handled in getPresentationJsonStringFromDictionaryRecurse. \ is handled by getPresentationJsonStringFromDictionary
        dictAllPaths[strFullPath] = entry
        
    rddAllPaths = recursivedefaultdict()
    for k,v in six.iteritems(dictAllPaths):
        addPresentationEntryToRdd(iter(k.lower().split("\\")), v, rddAllPaths)

    strJson = getPresentationJsonStringFromDictionary(rddAllPaths)

    #nSnapshotID is the _key but must be a string because _key cannot be a number
    dataToAdd = { "_key" : str(strSnapshotIDIn),
                  PERSEUS_UREG_PRESENTATION_JSON_FIELD_NAME : strJson }

    kvJson = Splunk_KV_Store.SplunkKVStore(PERSEUS_UREG_SNAPSHOT_PRESENTATION_JSON_KV_STORE_NAME)
    kvJson.addEntry(dataToAdd)

def deletePerseusUniversalRegSnapshotKVStore(strSnapshotIDIn = None):    
    kvRaw = Splunk_KV_Store.SplunkKVStore(PERSEUS_UREG_SNAPSHOT_RAW_KV_STORE_NAME)
    if (strSnapshotIDIn is None):
        kvRaw.removeAllEntries()
    else:
        kvRaw.removeMatchingEntries({ PERSEUS_UREG_SNAPSHOT_ID_FIELD_NAME : int(strSnapshotIDIn) })

def deletePerseusUniversalRegSnapshotInfoKVStore(strSnapshotIDIn = None):    
    kvSnapshot = Splunk_KV_Store.SplunkKVStore(PERSEUS_UREG_SNAPSHOT_INFO_KV_STORE_NAME)
    if (strSnapshotIDIn is None):
        kvSnapshot.removeAllEntries()
    else:
        kvSnapshot.removeMatchingEntries({ Splunk_KV_Store.SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME : strSnapshotIDIn })
        
def deletePerseusUniversalRegSnapshotPresentationKVStore(strSnapshotIDIn = None):
    kvPresentation = Splunk_KV_Store.SplunkKVStore(PERSEUS_UREG_SNAPSHOT_PRESENTATION_DATA_KV_STORE_NAME)
    if (strSnapshotIDIn is None):
        kvPresentation.removeAllEntries()
    else:
        kvPresentation.removeMatchingEntries({ PERSEUS_UREG_SNAPSHOT_ID_FIELD_NAME : int(strSnapshotIDIn) })

def deletePerseusUniversalRegSnapshotPresentationKeyToEventsLookupKVStore(strSnapshotIDIn = None):
    kvEvents = Splunk_KV_Store.SplunkKVStore(PERSEUS_UREG_SNAPSHOT_PRESENTATION_KEY_TO_EVENTS_KV_STORE_NAME)
    if (strSnapshotIDIn is None):
        kvEvents.removeAllEntries()
    else:
        kvEvents.removeMatchingEntries({ PERSEUS_UREG_SNAPSHOT_ID_FIELD_NAME : int(strSnapshotIDIn) })
        
def deletePerseusUniversalRegSnapshotPresentationJsonKVStore(strSnapshotIDIn = None):
    kvJson = Splunk_KV_Store.SplunkKVStore(PERSEUS_UREG_SNAPSHOT_PRESENTATION_JSON_KV_STORE_NAME)
    if (strSnapshotIDIn is None):
        kvJson.removeAllEntries()
    else:
        #nSnapshotID is the _key but must be a string because _key cannot be a number
        kvJson.removeMatchingEntries({ "_key" : str(strSnapshotIDIn) })

def createNewSnapshot():

    strSnapshotID = createNewUniversalRegSnapshot()        

    if (strSnapshotID is None):
        return
    
    #Shouldn't delete anything
    deletePerseusUniversalRegSnapshotPresentationKVStore(strSnapshotID)
    createPresentationForUniversalRegSnapshot(strSnapshotID)

    #Intentionally not deleting this
    createPresentationKeyToEventsForUniversalRegSnapshot(strSnapshotID)

    #Shouldn't delete anything
    deletePerseusUniversalRegSnapshotPresentationJsonKVStore(strSnapshotID)
    createJsonForPresentationAndAddToKVStore(strSnapshotID)

    return strSnapshotID
    
def deleteAllSnapshotsAndCreateNewSnapshot():

    deletePerseusUniversalRegSnapshotKVStore()
    deletePerseusUniversalRegSnapshotInfoKVStore()
    deletePerseusUniversalRegSnapshotPresentationKVStore()
    deletePerseusUniversalRegSnapshotPresentationKeyToEventsLookupKVStore()
    deletePerseusUniversalRegSnapshotPresentationJsonKVStore()
    
    return createNewSnapshot()

if __name__ == "__main__":

    try:
        #strSnapshotID = deleteAllSnapshotsAndCreateNewSnapshot()
        strSnapshotID = createNewSnapshot()

        if (strSnapshotID):
            Perseus_Management_Log.PerseusManagementLog().logCreateURegSnapshotSuccess("Created Snapshot " + str(strSnapshotID))
        else:
            Perseus_Management_Log.PerseusManagementLog().logCreateURegSnapshotSuccess("No New Snapshot Data")
            
    except Exception as err:
        Perseus_Management_Log.PerseusManagementLog().logCreateURegSnapshotFailure("Create Snapshot Failed with Error: " + str(err))
         
