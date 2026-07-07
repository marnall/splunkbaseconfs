#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import Splunk_Main
import Splunk_KV_Store
import Perseus_Management_Log

import VirusTotal

import sys
import time

ADD_VT_API_KEY_CMD_ARG_LC = "-addvirustotalkey"

PERSEUS_INTEGRATION_CREDENTIALS_KV_STORE_NAME = "PerseusIntegrationCredentials"

PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_NAME_FIELD_NAME = "strIntegrationName"

PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_API_KEY_FIELD_NAME = "strIntegrationApiKey"
PERSEUS_INTEGRATION_CREDENTIALS_API_KEY_FUNCTION_NAME = "strIntegrationApiKeyFunction"
PERSEUS_INTEGRATION_CREDENTIALS_LAST_USE_TIME = "dtLastUseTime"

PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_NAME_VIRUS_TOTAL_VALUE = "VirusTotal"
PERSEUS_INTEGRATION_CREDENTIALS_API_KEY_FUNCTION_VT_SCHEDULED_SEARCH = "Scheduled"
PERSEUS_INTEGRATION_CREDENTIALS_API_KEY_FUNCTION_VT_USER_INITIATED = "User"

def processCommandLine():

    dictCommandLine = {}

    for nArg in range(1, len(sys.argv)):
        strArgLC = sys.argv[nArg].lower()

        #Single value argument
        if (strArgLC == ADD_VT_API_KEY_CMD_ARG_LC):
            nArg += 1
            dictCommandLine[strArgLC] = sys.argv[nArg]

    return dictCommandLine

def PerseusIntegrationException(Exception):
    pass
    
def PerseusIntegrationCredentialsDoNotExist(PerseusIntegrationException):
    pass

def addIntegrationKey(strIntegrationNameIn, strIntegrationApiKeyIn, strIntegrationApiKeyFunctionIn = None, strIntegrationApiKeyInfoIn = None):

    try:
        dictIntegrationInfo = { "strIntegrationName" : strIntegrationNameIn,
                                "strIntegrationApiKey" : strIntegrationApiKeyIn,
                                "strIntegrationApiKeyFunction" : strIntegrationApiKeyFunctionIn,
                                "strIntegrationApiKeyInfo" : strIntegrationApiKeyInfoIn,     
                                "dtCreationTime" : time.time() }

        kvIntegrations = Splunk_KV_Store.SplunkKVStore(PERSEUS_INTEGRATION_CREDENTIALS_KV_STORE_NAME)
        kvIntegrations.addEntry(dictIntegrationInfo)
        
    except Exception as err:
        raise PerseusIntegrationException(err)
    
def updateIntegrationKeyLastUseTime(strIntegrationApiKeyIn, dtTimeIn = None):

    try:
        if (dtTimeIn is None):
            dtTimeIn = time.time()
        
        kvIntegrations = Splunk_KV_Store.SplunkKVStore(PERSEUS_INTEGRATION_CREDENTIALS_KV_STORE_NAME) 

        dictMatch = { PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_API_KEY_FIELD_NAME : strIntegrationApiKeyIn }
        dictEntry = kvIntegrations.getEntries(dictMatch)[0]
        dictEntry[PERSEUS_INTEGRATION_CREDENTIALS_LAST_USE_TIME] = dtTimeIn

        kvIntegrations.upsertEntry(dictEntry, dictMatch)

    except:
        raise PerseusIntegrationCredentialsDoNotExist()

def getIntegrationKeyLastUseTime(strIntegrationApiKeyIn):

    try:
         
        kvIntegrations = Splunk_KV_Store.SplunkKVStore(PERSEUS_INTEGRATION_CREDENTIALS_KV_STORE_NAME) 

        dictMatch = { PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_API_KEY_FIELD_NAME : strIntegrationApiKeyIn }
        return kvIntegrations.getEntries(dictMatch)[0][PERSEUS_INTEGRATION_CREDENTIALS_LAST_USE_TIME]
        
    except:
        raise PerseusIntegrationCredentialsDoNotExist()

#VirusTotal
PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_NAME_VIRUS_TOTAL_VALUE = "VirusTotal"
PERSEUS_INTEGRATION_CREDENTIALS_API_KEY_FUNCTION_VT_SCHEDULED_SEARCH = "Scheduled"
PERSEUS_INTEGRATION_CREDENTIALS_API_KEY_FUNCTION_VT_USER_INITIATED = "User"

#Returns a tuple with the key and whether the key is for the preferred function
def getVirusTotalApiKeyFromIntegrationKvStore(strPreferredFunctionIn):

    try:
        dictSearch = { PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_NAME_FIELD_NAME : PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_NAME_VIRUS_TOTAL_VALUE }
                             
        kvIntegrations = Splunk_KV_Store.SplunkKVStore(PERSEUS_INTEGRATION_CREDENTIALS_KV_STORE_NAME)
        lstResults = kvIntegrations.getEntries(dictSearch)

        if (len(lstResults) == 0):
            raise PerseusIntegrationCredentialsDoNotExist()
        
        #If the field does not exist for some reason, caught by exception handler

        #!TFinish - OPTIONAL - Add cycling code here that selects the matching function typet has the oldest dtLastUseTime
        for result in lstResults:
            try:
                if (result[PERSEUS_INTEGRATION_CREDENTIALS_API_KEY_FUNCTION_NAME] == strPreferredFunctionIn):
                    return result[PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_API_KEY_FIELD_NAME], True
            #Keep trying other keys. If it doesn't work, the exception will be generated below
            except:
                pass

        #If we couldn't find the preferred function, we just go with the first entry
        return lstResults[0][PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_API_KEY_FIELD_NAME], False
        
    except:
        raise PerseusIntegrationCredentialsDoNotExist()


def noVirusTotalApiKeyExists():
    try:
        #We aren't checking for any specific function
        getVirusTotalApiKeyFromIntegrationKvStore("None")
        return False
    except:
        return True

def addVirusTotalApiKey(strApiKeyIn):
    try:
        
        #At the moment we don't support adding multiple API keys through Python, only the Perseus Engine
        if (not noVirusTotalApiKeyExists()):
            raise Exception("A VirusTotal API Key Already Exists")

        strApiKeyIn = strApiKeyIn.strip()

        if (strApiKeyIn == "ENTER_VIRUSTOTAL_API_KEY_HERE"):
            raise Exception("Replace ENTER_VIRUSTOTAL_API_KEY_HERE with Your VirusTotal API Key")

        try:

            vt = VirusTotal.VirusTotal(strApiKeyIn)
            if (not vt.verifyApiKey()):
                raise Exception()
            
        except:
            raise Exception("Could Not Connect to VirusTotal with the Specified API Key")

        if (not Splunk_Main.IS_PERSEUS_DEMO):
            addIntegrationKey(PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_NAME_VIRUS_TOTAL_VALUE, strApiKeyIn, PERSEUS_INTEGRATION_CREDENTIALS_API_KEY_FUNCTION_VT_SCHEDULED_SEARCH)
        #In the Demo, the VT key is a user-initiated one because no scheduled search runs to look up MD5s
        else:
            addIntegrationKey(PERSEUS_INTEGRATION_CREDENTIALS_INTEGRATION_NAME_VIRUS_TOTAL_VALUE, strApiKeyIn, PERSEUS_INTEGRATION_CREDENTIALS_API_KEY_FUNCTION_VT_USER_INITIATED)
            
        print ("Status")
        print ("VirusTotal API Key Verified and Added")

        Perseus_Management_Log.PerseusManagementLog().logAddIntegrationCredentialsSuccess("VirusTotal " + strApiKeyIn)
        
    except Exception as err:
        print ("Error")
        print ("Adding VirusTotal API Key Failed: " + str(err))

        Perseus_Management_Log.PerseusManagementLog().logAddIntegrationCredentialsFailure(str(err))
        
if __name__ == "__main__":

    try:
        dictCmdArgs = processCommandLine()

        if (ADD_VT_API_KEY_CMD_ARG_LC  in dictCmdArgs):
            addVirusTotalApiKey(dictCmdArgs[ADD_VT_API_KEY_CMD_ARG_LC])

    except Exception as err:

        Perseus_Management_Log.PerseusManagementLog().logAddIntegrationCredentialsFailure("Unhandled Error: " + str(err))
