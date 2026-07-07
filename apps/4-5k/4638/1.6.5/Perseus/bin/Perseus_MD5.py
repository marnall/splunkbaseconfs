#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import six

import Splunk_Search
import Splunk_KV_Store
import VirusTotal
import Perseus_Integration_Credentials
import Perseus_Management_Log
import Perseus_Health

import datetime
import time

import sys

PERSEUS_ANALYZE_MD5_SCHEDULED_SEARCH_NAME = "Scheduled_Script_PerseusMD5"

MD5_CMD_ARG_LC = "-md5"
SCHEDULED_CMD_ARG_LC = "-scheduled"
EXECUTION_TIME_IN_SECS_CMD_ARG_LC = "-executiontime"
EXECUTION_END_UNIX_TIME_CMD_ARG_LC = "-executionend"

EXECUTION_TIME_INFINITE = -1

def processCommandLine():

    dictCommandLine = {}

    for nArg in range(1, len(sys.argv)):
        strArgLC = sys.argv[nArg].lower()

        #No value argument
        if (strArgLC == SCHEDULED_CMD_ARG_LC):
            dictCommandLine[strArgLC] = ""
        #Single value argument
        elif ((strArgLC == MD5_CMD_ARG_LC) or (strArgLC == EXECUTION_TIME_IN_SECS_CMD_ARG_LC) or (strArgLC == EXECUTION_END_UNIX_TIME_CMD_ARG_LC)):
            nArg += 1
            dictCommandLine[strArgLC] = sys.argv[nArg]

    return dictCommandLine

VT_MD5_HASH_KV_STORE_NAME = "VirusTotalMD5HashInfo"
VT_MD5_HASH_KV_MALICIOUS_COUNT_FIELD_NAME = "nMaliciousScanCount"
VT_MD5_HASH_KV_TOTAL_COUNT_FIELD_NAME = "nTotalScanCount"
VT_MD5_HASH_KV_REPUTATION_SCORE_FIELD_NAME = "nReputationScore"
VT_MD5_HASH_KV_GOODWARE_INDEX_FIELD_NAME = "nGoodwareIndex"
VT_MD5_HASH_KV_PERMALINK_FIELD_NAME = "strPermaLink"
#Linux Timestamp
VT_MD5_HASH_KV_REPORT_LOOKUP_TIME_FIELD_NAME = "dtReportLookupTime"

#We do not use _key here because search table won't return _key in its fields list
VT_MD5_HASH_SEARCH_MD5_FIELD_NAME = "MD5"

#If this is changed, update the Perseus UI Code That Checks for This Error
VT_MD5_NO_VIRUSTOTAL_API_KEY_ERROR_MESSAGE = "No VirusTotal API Key Exists for Authentication"

#!TFinish - OPTIONAL - 1 hour after first failure may be too soon to try again. Perhaps 4 hours
class FailedHash(object):

    def __init__(self, strHashIn):
        self.strHash = strHashIn
        self.nFailTimes = 1
        #After the first failure, we wait an hour before we attempt to lookup the hash again
        self.dtNextAttemptTime = datetime.datetime.now() + datetime.timedelta(hours=1)

    def __eq__(self, compare):

        if (six.PY2):
            bCompareIsString = ((type(compare) is str) or (type(compare) is unicode))
        #Python 3 Unicode Strings are of type str
        else:
            bCompareIsString = (type(compare) is str)
                
        if (bCompareIsString):        
            return (self.strHash == compare)
        else:
            return (self.strHash == compare.strHash)
    
    def getHash(self):
        return self.strHash

    def getFailTimes(self):
        return self.nFailTimes
    
    def getNextAttemptTime(self):
         return self.dtNextAttemptTime 
    
    def incrementFailure(self):
        self.nFailTimes += 1

        #The second time it fails we wait 4 hours
        if (self.nFailTimes == 2):
            self.dtNextAttemptTime = datetime.datetime.now() + datetime.timedelta(hours=4)
        #We wait a day after each subsequent failure
        else:
            self.dtNextAttemptTime = datetime.datetime.now() + datetime.timedelta(hours=24)
            
class HashesToProcess(object):

    #The first entry in the list is the newest (default Splunk sort order)
    def __init__(self, tupNewLowPriorityAndFailureStatusResetHashesIn):
        self.dictAllHashes = {}
        self.stackOldHashes = []

        #Low Priority Hashes go at the bottom of the stack
        for strHash in reversed(tupNewLowPriorityAndFailureStatusResetHashesIn[1]):               
            self.dictAllHashes[strHash] = False
            self.stackOldHashes.append(strHash)

        self.nIndexAfterLastLowPriorityHash = len(self.stackOldHashes)
        
        for strHash in reversed(tupNewLowPriorityAndFailureStatusResetHashesIn[0]):
            self.dictAllHashes[strHash] = False
            self.stackOldHashes.append(strHash)

        #We don't need to reset failure status of hashes because none are populated
            
        #It is beneficial to have a stack of new hashes (instead of merely appending them to top of stack) because new hashes are processed ahead of failed hashes which are processed ahead of old hashes
        self.stackNewHashes = []
        self.queueFailedHashes = []
        self.lstPendingHashes = []
        self.lstPendingFailedHashes = []

    #The first entry in the list is the newest (default Splunk sort order)
    def addNewHashes(self, tupNewLowPriorityAndFailureStatusResetHashesIn):

        #Remove Failure Status of New User-Requested Hash Lookup
        #NOTE: We do this first so that in the Normal Priority step below, the hash will be in stackOldHashes
        self.removeHashesFromFailureQueue(tupNewLowPriorityAndFailureStatusResetHashesIn[2])
        
        #Process the New Normal Priority Hashes
        for strHash in reversed(tupNewLowPriorityAndFailureStatusResetHashesIn[0]):
            
            if strHash not in self.dictAllHashes:
                self.dictAllHashes[strHash] = False
                self.stackNewHashes.append(strHash)
            else:
                try:
                    #If the hash already exists, doesn't have a VT entry already, and isn't in stackOldHashes, that means it in the failure queue. If it is in the failure queue, we don't want to add it to stackNewHashes because it shouldn't be processed. The only exception to that is if a user specifically requests a lookup on a hash that had previously failed. But that case is handled because it is removed from the failure queue and re-added to the stackOldHashes
                    self.stackOldHashes.remove(strHash)
                    self.stackNewHashes.append(strHash)
                #Ignore this because often times the hash will not be in the old hashes and we don't want to add it to stackNewHashes in those cases
                except:
                    pass         
        
        #Low Priority Hashes always gets added to the stackOldHashes below any normal priority hashes but ahead of any older low priority hashes
        for strHash in reversed(tupNewLowPriorityAndFailureStatusResetHashesIn[1]):
            if strHash not in self.dictAllHashes:
                self.dictAllHashes[strHash] = False
                self.stackOldHashes.insert(self.nIndexAfterLastLowPriorityHash, strHash)
                self.nIndexAfterLastLowPriorityHash += 1
            else:
                try:
                    #If the hash already exists, doesn't have a VT entry already, and isn't in stackOldHashes, that means it in the failure queue. If it is in the failure queue, we don't want to add it to stackNewHashes because it shouldn't be processed. The only exception to that is if a user specifically requests a lookup on a hash that had previously failed. But that case is handled because it is removed from the failure queue and re-added to the stackOldHashes
                    self.stackOldHashes.remove(strHash)
                    #We subtract one from the last index because removing it resulted in the list getting shorter - we also don't need to increment because the total size of the list didn't change
                    self.stackOldHashes.insert(self.nIndexAfterLastLowPriorityHash - 1, strHash)
                #Ignore this because often times the hash will not be in the old hashes and we don't want to add it to stackNewHashes in those cases
                except:
                    pass
    
    def getHashes(self, nMaxHashesIn):
        
        lstHashesRet = []

        #First attempt to check the new hashes that have come in
        while ((len(self.stackNewHashes) > 0) and (len(lstHashesRet) < nMaxHashesIn)):
            strHash = self.stackNewHashes.pop()
            lstHashesRet.append(strHash)
            self.lstPendingHashes.append(strHash)
      
        #Next we attempt to re-check failed hashes 
        while ((len(self.queueFailedHashes) > 0) and (len(lstHashesRet) < nMaxHashesIn)):

            #The first entry in the queue is the one that has the earliest run time - if we haven't reached that time yet we can skip the rest
            if (datetime.datetime.now() < self.queueFailedHashes[0].getNextAttemptTime()):
                break
            
            failedHash = self.queueFailedHashes.pop(0)
            lstHashesRet.append(failedHash.getHash())
            self.lstPendingFailedHashes.append(failedHash)
            
        #Last we do old hashes
        while ((len(self.stackOldHashes) > 0) and (len(lstHashesRet) < nMaxHashesIn)):
            strHash = self.stackOldHashes.pop()
            lstHashesRet.append(strHash)
            self.lstPendingHashes.append(strHash)


        return lstHashesRet
         
    def flagFailedHashes(self, lstFailedHashesIn):
        lstFailedHashesToAdd = []

        #Create a new FailedHash structure if it was first failure or increment failure otherwise
        for strHash in lstFailedHashesIn:
            if strHash in self.lstPendingHashes:
                lstFailedHashesToAdd.append(FailedHash(strHash))
            else:
                for failedHash in self.lstPendingFailedHashes:
                    if (failedHash.getHash() == strHash):
                        failedHash.incrementFailure()
                        lstFailedHashesToAdd.append(failedHash)
                        break

        #Add hashes to the failed hash list
        for failedHash in lstFailedHashesToAdd:
            bAdded = False
            #Insert it in the priority queue with the earliest next attempt time first
            for nIndex in range(0, len(self.queueFailedHashes)):
                if (self.queueFailedHashes[nIndex].getNextAttemptTime() > failedHash.getNextAttemptTime()):
                    self.queueFailedHashes.insert(nIndex, failedHash)
                    bAdded = True
                    break
                
            if (not bAdded):
                self.queueFailedHashes.append(failedHash)

        #Clear the rest of the lists because the other hashes were successful
        self.lstPendingHashes = []
        self.lstPendingFailedHashes = []

    def removeHashesFromFailureQueue(self, lstHashesIn):
         for strHash in lstHashesIn:
            try:
                self.queueFailedHashes.remove(strHash)
                #We put the hash back onto the old hashes stack so it can be processed properly. If a hash wasn't already in queueFailedHashes, that means it should already be in stackOldHashes
                self.stackOldHashes.append(strHash)
            except:
                pass
                
#Returns a tuple with the VT instance and whether it matches the preferred function
#!TFinish - OPTIONAL - Populate strIntegrationApiKeyInfo if the key is a private VT key and return this info so the time between calls and hash limits can be handled differently than the lower-rate public key
def getVirusTotalInstance(bUserInitiatedIn):
    try:
        strPreferredFunction = Perseus_Integration_Credentials.PERSEUS_INTEGRATION_CREDENTIALS_API_KEY_FUNCTION_VT_SCHEDULED_SEARCH
        if (bUserInitiatedIn):
            strPreferredFunction = Perseus_Integration_Credentials.PERSEUS_INTEGRATION_CREDENTIALS_API_KEY_FUNCTION_VT_USER_INITIATED
        
        strVirusTotalApiKey, bIsPreferredFunction = Perseus_Integration_Credentials.getVirusTotalApiKeyFromIntegrationKvStore(strPreferredFunction)
        return VirusTotal.VirusTotal(strVirusTotalApiKey), bIsPreferredFunction

    #If we cannot get the VirusTotal API Key Info for any reason, we roll over to the default (which may or may not be populated)            
    except:
        if (len(VirusTotal.virusTotalDefault.getAPIKey()) == 0):
            raise Exception("No VirusTotal API Key Exists")
        else:
            return VirusTotal.virusTotalDefault
            
#These should already be checked for duplicates
def getVirusTotalMD5ReportsAndAddToKVStore(vtIn, lstHashesIn):

    lstHashesAddedRet = []
    
    if (len(lstHashesIn) == 0):
        return []
        
    #If we wanted to check if MD5 Hash was present again, we'd use this: if (len(kvMD5.Entries( { "_key" : strHashIn })) == 0):
    lstReportsData = vtIn.getFileScanReportsImportantFields(lstHashesIn)

    lstEntries = []
    
    for strHash, nMaliciousCount, nTotalCount, strPermalink in lstReportsData:
        #We explicitly specify _key because VT_MD5_HASH_SEARCH_MD5_FIELD_NAME is not _key (_key will not appear in search table since it is listed as an internal field)
        #We explicitly cast strHash to string to make sure purely numeric hashes aren't auto-coerced to an integer
        lstEntries.append({ "_key" : str(strHash),
                             VT_MD5_HASH_KV_MALICIOUS_COUNT_FIELD_NAME : int(nMaliciousCount),
                             VT_MD5_HASH_KV_TOTAL_COUNT_FIELD_NAME : int(nTotalCount),
                             VT_MD5_HASH_KV_PERMALINK_FIELD_NAME : strPermalink,
                             VT_MD5_HASH_KV_REPORT_LOOKUP_TIME_FIELD_NAME : time.time()
                           })

        lstHashesAddedRet.append(strHash)
        
    kvMD5 = Splunk_KV_Store.SplunkKVStore(VT_MD5_HASH_KV_STORE_NAME)
    kvMD5.addEntry(lstEntries)

    return lstHashesAddedRet

#nShowAllAutoExecTypesIn of 0 indicates types 0-1, 1 indicates 0-3, -1 indicates 2-3
def getMostRecentMD5Hashes(bUnauthorizedModsIn, bIncludeUserRequestedMD5sIn, nShowAllAutoExecTypesIn = 0, dtIndexEarliestIn = None, lstHashesToResetFailureStatusForInOut = None):

    strModTypeQuery = '(Event.LocMod.LocModType="audit" OR Event.LocMod.LocModType="block")'
    if (not bUnauthorizedModsIn):
        strModTypeQuery = '(Event.LocMod.LocModType="permit")'
        
    strTimeQuery = ""
    if (dtIndexEarliestIn):
        strTimeQuery = "_index_earliest=" + str(dtIndexEarliestIn)

    strAppendUserMD5s = ""
    if (bIncludeUserRequestedMD5sIn):
        #The user request must have been in the last hour and we set _time to 2147483647 so it is the largest possible time, ensuring these user-initiated hash lookups get priority
        strAppendUserMD5s = ' | append [ | inputlookup PerseusManagementLog WHERE strOperation="AnalyzeMD5" ' + Perseus_Management_Log.PERSEUS_MANAGEMENT_LOG_RETURN_CODE_FIELD_NAME + '>0 | eval bRecent = if (dtExecutionTime - (now() - 3600) > 0, 1, 0) | search bRecent=1 | sort 0 -dtExecutionTime | rename strMessage AS MD5 | eval _time = 2147483647 ]'
                      
    strSearchQuery = ('`PerseusIndex` ' + strModTypeQuery +
                      ' AND "Event.LocMod.LocEntry.AutoExecFiles.AutoExecFile.AEFAttributes.AEFAttribute.AEFAttrMD5"=* ' + strTimeQuery +
                      ' | table _time, Event.LocMod.Location.LocGuid, "Event.LocMod.LocEntry.AutoExecFiles.AutoExecFile.AEFAttributes.AEFAttribute.AEFAttrMD5" ' + 
                      ' | `GetUnauthorizedModsFilterAutoExecType(' + str(nShowAllAutoExecTypesIn) + ')`'
                      ' | rename "Event.LocMod.LocEntry.AutoExecFiles.AutoExecFile.AEFAttributes.AEFAttribute.AEFAttrMD5" AS ' + VT_MD5_HASH_SEARCH_MD5_FIELD_NAME +
                      ' | mvexpand ' + VT_MD5_HASH_SEARCH_MD5_FIELD_NAME +
                      strAppendUserMD5s + 
                      ' | sort 0 -_time, +' + Perseus_Management_Log.PERSEUS_MANAGEMENT_LOG_RETURN_CODE_FIELD_NAME + ' | dedup ' + VT_MD5_HASH_SEARCH_MD5_FIELD_NAME +
                      ' | lookup VirusTotalMD5HashInfo _key AS ' + VT_MD5_HASH_SEARCH_MD5_FIELD_NAME + ' OUTPUT _key AS bHashAlreadyPresent | where isnull(bHashAlreadyPresent)'
                      ' | table _time, ' + VT_MD5_HASH_SEARCH_MD5_FIELD_NAME + ', ' + Perseus_Management_Log.PERSEUS_MANAGEMENT_LOG_RETURN_CODE_FIELD_NAME )
    
    query = Splunk_Search.SplunkSearchQuery(strSearchQuery)
    jsonResults = query.executeQueryAndGetJsonResults()

    lstMD5HashesRet = []
    for result in jsonResults:
        strMD5 = result[VT_MD5_HASH_SEARCH_MD5_FIELD_NAME]
        lstMD5HashesRet.append(strMD5)

        #Return code of 1 indicates a pending lookup of the MD5 that hasn't yet been processed. When user issues a new request, we override the failure status of the hash since they are actively indicating they want to try again
        if ((lstHashesToResetFailureStatusForInOut is not None) and (Perseus_Management_Log.PERSEUS_MANAGEMENT_LOG_RETURN_CODE_FIELD_NAME in result) and (int(result[Perseus_Management_Log.PERSEUS_MANAGEMENT_LOG_RETURN_CODE_FIELD_NAME]) == Perseus_Management_Log.PERSEUS_MANAGEMENT_LOG_RETURN_CODE_PENDING)):
            lstHashesToResetFailureStatusForInOut.append(strMD5)
            #Flag this as being processed so on subsequent queries, we do not treat this as a new request. If it is an old request that is in the failure queue, it won't be added in addNewHashes. But we don't want to remove it from the failure queue unless it is a new request
            Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5PendingProcessed(strMD5)
        
    return lstMD5HashesRet
   
#Returns a tuple of hashes, low priority hashes, and hashes to reset failure status of because user issued a new request to lookup MD5 
def getMostRecentUnauthorizedMD5Hashes(dtIndexEarliestIn = None):

    lstHashesToResetFailureStatusFor = []
    
    lstHashes = getMostRecentMD5Hashes(True, True, 0, dtIndexEarliestIn, lstHashesToResetFailureStatusFor)
    #No need to retrieve the user-requested hashes twice since they already were retrieved above
    lstLowPriorityHashes = getMostRecentMD5Hashes(True, False, -1, dtIndexEarliestIn, lstHashesToResetFailureStatusFor)
    return lstHashes, lstLowPriorityHashes, lstHashesToResetFailureStatusFor

#funcGetHashesFuncIn should return a tuple of hashes, low priority hashes, and hashes to reset failure status of because user issued a new request to lookup MD5 
def analyzeMD5Hashes(nExecutionTimeInSecsIn, funcGetHashesFuncIn, bRaiseExceptionOnFailureIn):

    MAX_HASHES_TO_SEND_TO_VT = 4
    TIME_BETWEEN_VT_CALLS_IN_SECS = 60
    TIME_BETWEEN_GET_EVENTS_CALLS_IN_SECS = 5 * 60

    try:
        vt, bScheduledFunctionExists = getVirusTotalInstance(False)
    except:
        raise Exception(VT_MD5_NO_VIRUSTOTAL_API_KEY_ERROR_MESSAGE)
       
    nStartTime = time.time()
    nEndTime = nStartTime + nExecutionTimeInSecsIn
    nEarliestTimeNewHashes = nStartTime
    
    hashesToProcess = HashesToProcess(funcGetHashesFuncIn())    
    nLastGetEventTime = time.time()

    perseusHealth = Perseus_Health.PerseusHealth()
    
    while ((nExecutionTimeInSecsIn == EXECUTION_TIME_INFINITE) or (time.time() < nEndTime)):

        #Indicate the Analyze MD5 Routine is currently running
        try:
            perseusHealth.updateAnalyzeMD5Time()
        #Ignore any errors here - should likely work next time
        except:
            pass
        
        #If 5 minutes have elapsed since we last got hashes, get any new hashes
        try:
            if (time.time() > (nLastGetEventTime + TIME_BETWEEN_GET_EVENTS_CALLS_IN_SECS)):
                nOldEarliestTimeNewHashes = nEarliestTimeNewHashes
                nEarliestTimeNewHashes = time.time()

                hashesToProcess.addNewHashes(funcGetHashesFuncIn(nOldEarliestTimeNewHashes))
                
                nLastGetEventTime = time.time()
        #Ignore Errors Unless We Throw Exception on Failure - We'll just use whatever hashes we already have in the list
        except Exception as err:
            if bRaiseExceptionOnFailureIn:
                raise Exception("Error Encountered Getting New Hashes - " + str(err))
        
        #Process Hashes
        lstHashes = hashesToProcess.getHashes(MAX_HASHES_TO_SEND_TO_VT)
                        
        try:
            lstAddedHashes = getVirusTotalMD5ReportsAndAddToKVStore(vt, lstHashes)

            lstFailedHashes = []
            for strHash in lstHashes:
                if (strHash not in lstAddedHashes):
                    lstFailedHashes.append(strHash)

            hashesToProcess.flagFailedHashes(lstFailedHashes)

            Perseus_Integration_Credentials.updateIntegrationKeyLastUseTime(vt.getAPIKey())

        except Exception as err:
            #Ignore Errors Unless We Throw Exception on Failure
            if bRaiseExceptionOnFailureIn:
                raise
            
        #Sleep after processing hashes
        time.sleep(TIME_BETWEEN_VT_CALLS_IN_SECS)

def analyzeUnauthorizedMD5Hashes(nExecutionTimeInSecsIn, bRaiseExceptionOnFailureIn):
    analyzeMD5Hashes(nExecutionTimeInSecsIn, getMostRecentUnauthorizedMD5Hashes, bRaiseExceptionOnFailureIn)

#Returns True if a VT Report could be found, False if not, and None if it is pending
def analyzeSingleMD5Hash(strHashIn, bRaiseExceptionOnFailureIn):
    try:
        vt, bUserFunctionExists = getVirusTotalInstance(True)
    except:
        if bRaiseExceptionOnFailureIn:
            raise Exception(VT_MD5_NO_VIRUSTOTAL_API_KEY_ERROR_MESSAGE)

    bUpdateLastUseTime = True
                        
    if (not bUserFunctionExists):

        #We create a pending log entry that will be picked up by the search
        try:

            dtLastUsedTime = Perseus_Integration_Credentials.getIntegrationKeyLastUseTime(vt.getAPIKey())

            #We check if this Integration Key has been used in the last 5 minutes. If it has, we return None to indicate pending should be used
            if (time.time() - dtLastUsedTime < 300):
                return None                        
            else:
                #We do not update last use time in this case because when scheduled search is not running, we want single MD5 calls to not queue
                bUpdateLastUseTime = False
                #Intentionally fall through below to use the Integration Key for MD5 lookup
             
            
        #Fall through below to see if it'll work (it probably won't) and to make it easier for caller to identify the error
        except:
             pass


    #We don't need to share the API key with the scheduled search, so we don't need to add it to a pending queue and can use the key to lookup the MD5 immediately
    try:
        #Return true if we found info for the entry
        bRetVal = (len(getVirusTotalMD5ReportsAndAddToKVStore(vt, [ strHashIn ])) > 0)

        try:
            if bUpdateLastUseTime:
                Perseus_Integration_Credentials.updateIntegrationKeyLastUseTime(vt.getAPIKey())
        #Failure to update the Last Use Time isn't significant enough to raise an error when checking a single MD5
        except:
            pass
                        
        return bRetVal
    except Exception as err:
        if bRaiseExceptionOnFailureIn:
            raise

    return False

if __name__ == "__main__":

    nNextScheduledTime = None

    try:
        dictCmdArgs = processCommandLine()
        
        #Analyze single hash that was passed in
        if (MD5_CMD_ARG_LC in dictCmdArgs):
            strHash = dictCmdArgs[MD5_CMD_ARG_LC]

            #We raise the error and let it pass through so the caller can see an error was encountered
            bResult = analyzeSingleMD5Hash(strHash, True)
            
            if (bResult is None):
                #We want an exception raised if this fails because this capability won't work if it is not logged correctly
                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Pending(strHash, False)
            elif (bResult):
                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Success(strHash)
            else:
                #We consider this a "success" in that everything functioned as intended even though there was no data to retrieve
                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Success("No VirusTotal Report Found for " + strHash)
        else:
            #!TFinish - OPTIONAL - Add in some way of notifying this script (KV Store entry? Special Management Log entry?) it should abort. Perhaps pass the search sid into this function and have it monitor for search status in its loop

            #There is a 10 minute gap between the daily scheduled event - checking if it is active within the last 5 minutes should be safe (worst case scenario it doesn't run on schedule and is started by the Perseus Health check an hour later)
            if (Perseus_Health.PerseusHealth().analyzeMD5IsCurrentlyActive(5)):
                raise Exception("Analyze MD5 Is Already Running")
            
            if (EXECUTION_TIME_IN_SECS_CMD_ARG_LC in dictCmdArgs):
                nExecutionTimeInSecs = int(dictCmdArgs[EXECUTION_TIME_IN_SECS_CMD_ARG_LC])
            elif (EXECUTION_END_UNIX_TIME_CMD_ARG_LC in dictCmdArgs):
                nExecutionTimeInSecs = int(dictCmdArgs[EXECUTION_END_UNIX_TIME_CMD_ARG_LC]) - time.time()
            elif (SCHEDULED_CMD_ARG_LC in dictCmdArgs):

                try:
                    #This appears to not include the currently running scheduled search time if this is called as part of a running scheduled search (we could add 1 minute to the time here if we run into issues later)
                    nNextScheduledTime = Splunk_Search.SplunkSavedSearch("Scheduled_Script_PerseusMD5").getSavedSearchNextScheduledUnixTime()
                    #We end 10 minutes before the next scheduled time so there isn't any overlap
                    nExecutionTimeInSecs = nNextScheduledTime - time.time() - 600
                
                except Exception as err:
                    raise Exception("Could not retrieve schedule: " + str(err))

            else:
                #We raise an error here so that a user doesn't start this from the command line accidentally resulting in it running indefinitely
                raise Exception("An -ExecutionTime must be provided that specifies how many seconds Perseus should analyze hashes for")

            if (EXECUTION_TIME_IN_SECS_CMD_ARG_LC in dictCmdArgs):
                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Success("All Unauthorized for " + str(nExecutionTimeInSecs) + " Seconds Started")
            elif (EXECUTION_END_UNIX_TIME_CMD_ARG_LC in dictCmdArgs):
                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Success("All Unauthorized Until " + str(dictCmdArgs[EXECUTION_END_UNIX_TIME_CMD_ARG_LC]) + " Started")
            else:
                if (nNextScheduledTime is None):
                    nNextScheduledTime = "Next Scheduled Time"

                #NOTE: This message may appear to be out of sequence in the PerseusManagementLog if we encounter an error immediately after starting since the resolution of the dtExecutionTime isn't precise enough  
                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Success("All Unauthorized Until " + str(nNextScheduledTime) + " Started")
                
            #We continue if we run into any exceptions other than no VirusTotal Integration Key existing
            analyzeUnauthorizedMD5Hashes(nExecutionTimeInSecs, False)

            if (EXECUTION_TIME_IN_SECS_CMD_ARG_LC in dictCmdArgs):
                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Success("All Unauthorized for " + str(nExecutionTimeInSecs) + " Seconds Completed")    
            elif (EXECUTION_END_UNIX_TIME_CMD_ARG_LC in dictCmdArgs):
                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Success("All Unauthorized Until " + str(dictCmdArgs[EXECUTION_END_UNIX_TIME_CMD_ARG_LC]) + " Completed")
            else:
                if (nNextScheduledTime is None):
                    nNextScheduledTime = "Next Scheduled Time"
                  
                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Success("All Unauthorized Until " + str(nNextScheduledTime) + " Completed")
                
                  
    except Exception as err:
        
        if (MD5_CMD_ARG_LC in dictCmdArgs):
            Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Failure("Analyze MD5 for " + dictCmdArgs[MD5_CMD_ARG_LC] + " Failed with Error: " + str(err))
        else:

            if (EXECUTION_TIME_IN_SECS_CMD_ARG_LC in dictCmdArgs):
                nExecutionTimeInSecs = EXECUTION_TIME_INFINITE

                if (EXECUTION_TIME_IN_SECS_CMD_ARG_LC in dictCmdArgs):
                    nExecutionTimeInSecs = dictCmdArgs[EXECUTION_TIME_IN_SECS_CMD_ARG_LC]

                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Failure("Analyze MD5 All Unauthorized for " + str(nExecutionTimeInSecs) + " Seconds Failed with Error: " + str(err))
                
            elif (EXECUTION_END_UNIX_TIME_CMD_ARG_LC in dictCmdArgs):
                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Failure("Analyze MD5 All Unauthorized Until " + str(dictCmdArgs[EXECUTION_END_UNIX_TIME_CMD_ARG_LC]) + " Failed with Error: " + str(err))
            
            else:
                if (nNextScheduledTime is None):
                    nNextScheduledTime = "Next Scheduled Time"
                
                Perseus_Management_Log.PerseusManagementLog().logAnalyzeMD5Failure("Analyze MD5 All Unauthorized Until " + str(nNextScheduledTime) + " Failed with Error: " + str(err))


