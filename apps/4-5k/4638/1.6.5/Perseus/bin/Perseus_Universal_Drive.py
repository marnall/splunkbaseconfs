#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import six

import Splunk_Main
import Splunk_Search
import Splunk_KV_Store

import Perseus_Management_Log

from collections import defaultdict

#!TFinish - OPTIONAL - Detect incomplete snapshot by noting snapshot does not have dtSnapshotEndTime
#!TFinish - OPTIONAL - PerseusUniversalDriveSnapshotPresentationData and PerseusUniversalDriveSnapshotPresentationKeyToEventsPrep are essentially temporary stores. Add an option to delete these KV stores and reclaim disk space (see: https://answers.splunk.com/answers/613389/kvstore-mongodb-compact-command.html)\
#!TFinish - OPTIONAL = If an entry is marked as Blocked, REMOVE it from the snapshot for that system
#!TFinish - OPTIONAL - Compress the Json data for faster download and smaller KV store usage
 
PERSEUS_UDRIVE_SNAPSHOT_RAW_KV_STORE_NAME = "PerseusUniversalDriveSnapshotRawData"
PERSEUS_UDRIVE_SNAPSHOT_INFO_KV_STORE_NAME = "PerseusUniversalDriveSnapshotInfo"
PERSEUS_UDRIVE_SNAPSHOT_PRESENTATION_DATA_KV_STORE_NAME = "PerseusUniversalDriveSnapshotPresentationData"
PERSEUS_UDRIVE_SNAPSHOT_PRESENTATION_KEY_TO_EVENTS_KV_STORE_NAME = "PerseusUniversalDriveSnapshotPresentationKeyToEventsLookup"
PERSEUS_UDRIVE_SNAPSHOT_PRESENTATION_JSON_KV_STORE_NAME = "PerseusUniversalDriveSnapshotPresentationJson"
PERSEUS_UDRIVE_SNAPSHOT_ID_FIELD_NAME = "nSnapshotID"

PERSEUS_UDRIVE_AEF_FILE_FIELD_NAME = "strAEFFile"
PERSEUS_UDRIVE_OBJECT_NAME_FIELD_NAME = "strObjectName"

PERSEUS_UDRIVE_OBJECT_TYPE_FIELD_NAME = "strObjectType"
PERSEUS_UDRIVE_OBJECT_TYPE_FOLDER = "5"
PERSEUS_UDRIVE_REP_FIELD_NAME = "nRep"
PERSEUS_UDRIVE_REP_KNOWN_GOOD_VALUE = "-1"

PERSEUS_UDRIVE_HOSTS_WITHAEFFILE_FIELD_NAME = "nHostsWithAEFFile"

PERSEUS_UDRIVE_PRESENTATION_JSON_FIELD_NAME = "strJson"

class UniversalDriveException(Exception):
    pass

def createNewUniversalDriveSnapshot():

    try:
        query = Splunk_Search.SplunkSearchQuery(" | `PerseusUniversalDriveGetLastSnapshotInfo`", False)
        #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
        jsonResults = query.executeQueryAndGetJsonResults()

        strNewSnapshotIDOut = str(int(jsonResults[0]["SnapshotID"]) + 1)
        strEarliestIndexTime = jsonResults[0]["SnapshotStartTime"]

    except:
        raise UniversalDriveException("Previous Snapshot Info could not be retrieved. If this issue persists, please contact support@PerseusSec.com.")
     
    strQuery = '`PerseusUniversalDriveCreateSnapshotFromIndex(' + strNewSnapshotIDOut + ', ' + strEarliestIndexTime + ')`'

    dtSnapshotStartTime = Splunk_Main.getSplunkTimeForNow()
    
    query = Splunk_Search.SplunkSearchQuery(strQuery)
    #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
    jsonResults = query.executeQueryAndGetJsonResults()

    if (len(jsonResults) == 0):
        return None
    
    dtSnapshotEndTime = Splunk_Main.getSplunkTimeForNow()
    
    #Create Snapshot Info Entry
    strQuery = '| `PerseusUniversalDriveCreateSnapshotInfo(' + strNewSnapshotIDOut + ', ' + str(dtSnapshotStartTime) + ', ' + str(dtSnapshotEndTime) + ')`'
    
    query = Splunk_Search.SplunkSearchQuery(strQuery, False)
    #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
    query.executeQueryAndGetJsonResults()

    return strNewSnapshotIDOut

def createPresentationForUniversalDriveSnapshot(strSnapshotIDIn):

    strQuery = '| `PerseusUniversalDriveCreateSnapshotPresentation(' + strSnapshotIDIn + ')`'

    query = Splunk_Search.SplunkSearchQuery(strQuery, False)
    #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
    query.executeQueryAndGetJsonResults()

def createPresentationKeyToEventsForUniversalDriveSnapshot(strSnapshotIDIn):
    
    #Prepare the Temporary Lookup
    strQuery = '| `PerseusUniversalDriveCreateSnapshotPresentationKeyToEventsPrep(' + strSnapshotIDIn + ')`'

    query = Splunk_Search.SplunkSearchQuery(strQuery, False)
    #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
    query.executeQueryAndGetJsonResults()

    #Add the Key to Events Entries
    strQuery = '| `PerseusUniversalDriveAddSnapshotPresentationKeyEvents(' + strSnapshotIDIn + ')`'

    query = Splunk_Search.SplunkSearchQuery(strQuery, False)
    #Get the results instead of just executing and waiting for the search so that if an error was encountered, it is raised
    query.executeQueryAndGetJsonResults()

class recursivedefaultdict(defaultdict):
    def __init__(self):
        self.default_factory = type(self)
        
#Call this function by splitting the AEFFile path
def addPresentationEntryToRdd(itPathIn, entryDictIn, rddIn):
    try:
        addPresentationEntryToRdd(itPathIn, entryDictIn, rddIn[six.next(itPathIn)])
    #The node is reached when we hit Stop Iteration - we store the relevant entry data in the node
    except StopIteration:
        rddIn[Splunk_KV_Store.SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME] = entryDictIn[Splunk_KV_Store.SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME]
        rddIn[PERSEUS_UDRIVE_HOSTS_WITHAEFFILE_FIELD_NAME] = entryDictIn[PERSEUS_UDRIVE_HOSTS_WITHAEFFILE_FIELD_NAME]
        rddIn[PERSEUS_UDRIVE_REP_FIELD_NAME] = entryDictIn[PERSEUS_UDRIVE_REP_FIELD_NAME]

#!TFinish - OPTIONAL - This function could probably be optimizated (removing the sort for instance still works and gives about a 5% performance boost). However, this function takes less than 1% of the total snapshot time, so optimizing is not likely to signficantly impact snapshot performance unless we dramatically improve the other areas
def getPresentationJsonStringFromDictionaryRecurse(rddAllPathsIn, strKeyIn = None):
    
    if (strKeyIn is None):
        strJsonString = ""
    else:
        #We store with shorter name to decrease size of the json transfer
        #strJsonString += '{"t":"%s",' % (strKeyIn.replace('"', '\\"')
        #The replace in the above code is not explicitly needed because files/folders cannot contain ". This is omitted to increase performance
        strJsonString = '{"t":"%s",' % (strKeyIn)        
        
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

            if (strChildKey == PERSEUS_UDRIVE_REP_FIELD_NAME):
                #Since most files should be known good, we save space in the json by not adding the field
                if (child != PERSEUS_UDRIVE_REP_KNOWN_GOOD_VALUE):
                    strChildData += ('"r":' + str(child))

            #!TFinish - OPTIONAL - Enable this code if we begin tracking folder creation in the UDrive data
            #elif ((strNextKey == PERSEUS_UDRIVE_OBJECT_TYPE_JSON_FIELD_NAME) and (rddNext[strNextKey] == PERSEUS_UDRIVE_OBJECT_TYPE_FOLDER)):
            ##We flag this instead of setting it now because if one of the children is a recursivedefaultdict, folder is set there
            #bChildDataIsFolder = True

                    
            elif (strChildKey == PERSEUS_UDRIVE_HOSTS_WITHAEFFILE_FIELD_NAME):
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
    #Must wrap whole JSON in []. String is already json escaped
    strJsonString = ("[" + strJsonString + "]")
    
    return strJsonString

def createJsonForPresentationAndAddToKVStore(strSnapshotIDIn):

    kvPresentation = Splunk_KV_Store.SplunkKVStore(PERSEUS_UDRIVE_SNAPSHOT_PRESENTATION_DATA_KV_STORE_NAME)
    #strSnapshotIDIn must be converted to an int to return proper results
    lstEntries = kvPresentation.getEntriesNoMax({ PERSEUS_UDRIVE_SNAPSHOT_ID_FIELD_NAME : int(strSnapshotIDIn) })
    
    n = 0
    setAllPaths = set()
    dictAllPaths = {}
 
    rddAllPaths = recursivedefaultdict()
    for entry in lstEntries:
        #We only need to escape " and \ because all other json escape values are for whitespace characters. Neither is necessary for the UDrive because Files/Folders cannot have either character
        dictAllPaths[entry[PERSEUS_UDRIVE_AEF_FILE_FIELD_NAME]] = entry

    rddAllPaths = recursivedefaultdict()
    for k,v in six.iteritems(dictAllPaths):
        addPresentationEntryToRdd(iter(k.lower().split("\\")), v, rddAllPaths)

    strJson = getPresentationJsonStringFromDictionary(rddAllPaths)
    
    #nSnapshotID is the _key but must be a string because _key cannot be a number
    dataToAdd = { "_key" : str(strSnapshotIDIn),
                  PERSEUS_UDRIVE_PRESENTATION_JSON_FIELD_NAME : strJson }

    kvJson = Splunk_KV_Store.SplunkKVStore(PERSEUS_UDRIVE_SNAPSHOT_PRESENTATION_JSON_KV_STORE_NAME)
    kvJson.addEntry(dataToAdd)

def deletePerseusUniversalDriveSnapshotKVStore(strSnapshotIDIn = None):
    kvRaw = Splunk_KV_Store.SplunkKVStore(PERSEUS_UDRIVE_SNAPSHOT_RAW_KV_STORE_NAME)
    if (strSnapshotIDIn is None):
        kvRaw.removeAllEntries()
    else:
        kvRaw.removeMatchingEntries({ PERSEUS_UDRIVE_SNAPSHOT_ID_FIELD_NAME : int(strSnapshotIDIn) })

def deletePerseusUniversalDriveSnapshotInfoKVStore(strSnapshotIDIn = None):
    kvSnapshot = Splunk_KV_Store.SplunkKVStore(PERSEUS_UDRIVE_SNAPSHOT_INFO_KV_STORE_NAME)
    if (strSnapshotIDIn is None):
        kvSnapshot.removeAllEntries()
    else:
        kvSnapshot.removeMatchingEntries({ Splunk_KV_Store.SPLUNK_KV_STORE_DATA_KEY_FIELD_NAME : strSnapshotIDIn })
        
def deletePerseusUniversalDriveSnapshotPresentationKVStore(strSnapshotIDIn = None):
    kvPresentation = Splunk_KV_Store.SplunkKVStore(PERSEUS_UDRIVE_SNAPSHOT_PRESENTATION_DATA_KV_STORE_NAME)
    if (strSnapshotIDIn is None):
        kvPresentation.removeAllEntries()
    else:
        kvPresentation.removeMatchingEntries({ PERSEUS_UDRIVE_SNAPSHOT_ID_FIELD_NAME : int(strSnapshotIDIn) })

def deletePerseusUniversalDriveSnapshotPresentationKeyToEventsLookupKVStore(strSnapshotIDIn = None):
    kvEvents = Splunk_KV_Store.SplunkKVStore(PERSEUS_UDRIVE_SNAPSHOT_PRESENTATION_KEY_TO_EVENTS_KV_STORE_NAME)
    if (strSnapshotIDIn is None):
        kvEvents.removeAllEntries()
    else:
        kvEvents.removeMatchingEntries({ PERSEUS_UDRIVE_SNAPSHOT_ID_FIELD_NAME : int(strSnapshotIDIn) })
        
def deletePerseusUniversalDriveSnapshotPresentationJsonKVStore(strSnapshotIDIn = None):
    kvJson = Splunk_KV_Store.SplunkKVStore(PERSEUS_UDRIVE_SNAPSHOT_PRESENTATION_JSON_KV_STORE_NAME)
    if (strSnapshotIDIn is None):
        kvJson.removeAllEntries()
    else:
        #nSnapshotID is the _key but must be a string because _key cannot be a number
        kvJson.removeMatchingEntries({ "_key" : str(strSnapshotIDIn) })

def createNewSnapshot():

    strSnapshotID = createNewUniversalDriveSnapshot()        

    if (strSnapshotID is None):
        return
    
    #Shouldn't delete anything
    deletePerseusUniversalDriveSnapshotPresentationKVStore(strSnapshotID)
    createPresentationForUniversalDriveSnapshot(strSnapshotID)

    #Intentionally not deleting this
    createPresentationKeyToEventsForUniversalDriveSnapshot(strSnapshotID)
    
    #Shouldn't delete anything
    deletePerseusUniversalDriveSnapshotPresentationJsonKVStore(strSnapshotID)
    createJsonForPresentationAndAddToKVStore(strSnapshotID)

    return strSnapshotID
     
def deleteAllSnapshotsAndCreateNewSnapshot():
    deletePerseusUniversalDriveSnapshotKVStore()
    deletePerseusUniversalDriveSnapshotInfoKVStore()
    deletePerseusUniversalDriveSnapshotPresentationKVStore()
    deletePerseusUniversalDriveSnapshotPresentationKeyToEventsLookupKVStore()
    deletePerseusUniversalDriveSnapshotPresentationJsonKVStore()

    return createNewSnapshot()

if __name__ == "__main__":
    try:
        #strSnapshotID = deleteAllSnapshotsAndCreateNewSnapshot()
        strSnapshotID = createNewSnapshot()

        if (strSnapshotID):
            Perseus_Management_Log.PerseusManagementLog().logCreateUDriveSnapshotSuccess("Created Snapshot " + str(strSnapshotID))
        else:
            Perseus_Management_Log.PerseusManagementLog().logCreateUDriveSnapshotSuccess("No New Snapshot Data")
                                                                                         
    except Exception as err:
        Perseus_Management_Log.PerseusManagementLog().logCreateUDriveSnapshotFailure("Create Snapshot Failed with Error: " + str(err))
