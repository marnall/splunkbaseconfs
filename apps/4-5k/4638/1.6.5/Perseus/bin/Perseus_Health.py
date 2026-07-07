#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import Splunk_KV_Store
import Splunk_Search
import Perseus_Management_Log
import Perseus_Integration_Credentials
import Perseus_MD5

import time

PERSEUS_HEALTH_KV_STORE_NAME = "PerseusHealth"

PERSEUS_HEALTH_OPERATION_FIELD_NAME = "strOperation"
PERSEUS_HEALTH_OPERATION_ANALYZE_MD5_ACTIVE = "AnalyzeMD5Active"

PERSEUS_HEALTH_OPERATION_STATUS_FIELD_NAME = "nOperationStatus"
PERSEUS_HEALTH_OPERATION_STATUS_ACTIVE = 10

PERSEUS_HEALTH_OPERATION_TIME_FIELD_NAME = "dtOperationTime"

class PerseusHealth(Splunk_KV_Store.SplunkKVStore):

    def __init__(self):
        super(PerseusHealth, self).__init__(PERSEUS_HEALTH_KV_STORE_NAME)

    def updateAnalyzeMD5Time(self):
        dictEntry = { PERSEUS_HEALTH_OPERATION_FIELD_NAME : PERSEUS_HEALTH_OPERATION_ANALYZE_MD5_ACTIVE,
                      PERSEUS_HEALTH_OPERATION_STATUS_FIELD_NAME : PERSEUS_HEALTH_OPERATION_STATUS_ACTIVE,
                      PERSEUS_HEALTH_OPERATION_TIME_FIELD_NAME : time.time() }

        dictMatch = { PERSEUS_HEALTH_OPERATION_FIELD_NAME : PERSEUS_HEALTH_OPERATION_ANALYZE_MD5_ACTIVE,
                      PERSEUS_HEALTH_OPERATION_STATUS_FIELD_NAME : PERSEUS_HEALTH_OPERATION_STATUS_ACTIVE }
        
        super(PerseusHealth, self).upsertEntry(dictEntry, dictMatch)

    #Returns 0 if no Analyze MD5 Entry Exists
    def getAnalyzeMD5Time(self):
        
        dictMatch = { PERSEUS_HEALTH_OPERATION_FIELD_NAME : PERSEUS_HEALTH_OPERATION_ANALYZE_MD5_ACTIVE,
                      PERSEUS_HEALTH_OPERATION_STATUS_FIELD_NAME : PERSEUS_HEALTH_OPERATION_STATUS_ACTIVE }

        jsonEntries = super(PerseusHealth, self).getEntries(dictMatch)

        dtOperationTime = 0

        #There should be only one of these entries at any time. Just in case however, we'll return the most recent time if there are multiple
        for entry in jsonEntries:
            try:
                if (entry[PERSEUS_HEALTH_OPERATION_TIME_FIELD_NAME] > dtOperationTime):
                    dtOperationTime = entry[PERSEUS_HEALTH_OPERATION_TIME_FIELD_NAME]
                    
            #Ignore Operation Time Missing - Shouldn't Happen But 
            except:
                pass

        return dtOperationTime

    def analyzeMD5IsCurrentlyActive(self, nMaxMinutesSinceLastOperationTimeIn = 30):

        return ((self.getAnalyzeMD5Time() + (nMaxMinutesSinceLastOperationTimeIn * 60)) >= time.time())

    def conductHealthCheck(self):

        if ((not self.analyzeMD5IsCurrentlyActive()) and (not Perseus_Integration_Credentials.noVirusTotalApiKeyExists())):

            #We do not wait for this to end because it is long-running
            Splunk_Search.SplunkSavedSearch(Perseus_MD5.PERSEUS_ANALYZE_MD5_SCHEDULED_SEARCH_NAME).executeSearch(False)

            Perseus_Management_Log.PerseusManagementLog().logConductHealthCheckSuccess("Started AnalyzeMD5")
            
        #We only log if we performed some corrective action above
            
if __name__ == "__main__":

    try:
        PerseusHealth().conductHealthCheck()
        
    except Exception as err:
        Perseus_Management_Log.PerseusManagementLog().logConductHealthCheckFailure("Conduct Health Check Failed Failed with Error: " + str(err))
