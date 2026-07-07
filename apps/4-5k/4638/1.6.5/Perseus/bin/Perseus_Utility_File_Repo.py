#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import Splunk_KV_Store
import Splunk_Main

def getUtilityFileKvStoreEntryByKey(strKeyIn, headerIn = None):
    try:
        kvUtilityFileRepo = Splunk_KV_Store.SplunkKVStore("PerseusUtilityFileRepo", headerIn)
        lstEntries = kvUtilityFileRepo.getEntries({  "_key" : strKeyIn })
        
        if (len(lstEntries) == 0):
            raise Exception("The Utility File Does Not Exist")
        #If somehow there are more than 1 entries, we just get the first one
        else:
            return lstEntries[0]

    except Exception as err:

        raise Exception("Could Not Retrieve Utility File From Perseus with Error: " + str(err))    
