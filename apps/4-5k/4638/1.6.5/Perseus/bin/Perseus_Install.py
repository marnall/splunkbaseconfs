#COPYRIGHT (C) JOSEPH KOVACIC 2020 - ALL RIGHTS RESERVED
#Unauthorized copying, distribution, or reuse of this file or its contents, via any medium is strictly prohibited without written consent

import Splunk_Main
import Splunk_KV_Store
import Splunk_Config
import Perseus_Management_Log
import sys

PERSEUS_EVENT_INDEX_NAME = "perseus_event"

#NOTE: This function should only be use in non-clustered indexer environments
def createPerseusEventsIndex():
    try:
        Splunk_Main.createSplunkIndex(PERSEUS_EVENT_INDEX_NAME)
        #Verify that the index was actually created - will throw an error if it wasn't
        Splunk_Main.getSplunkIndexJson(PERSEUS_EVENT_INDEX_NAME)
    except Exception as err:
        raise Exception("Failed to create " + PERSEUS_EVENT_INDEX_NAME + " index with error " + str(err))
    
if __name__ == "__main__":

    logPerseus = Perseus_Management_Log.PerseusManagementLog()
    
    try:

        bSearchHeadCluster = False
        bSeparateIndexer = False
        
        #Parse Command Line to Determine if We are Installing into a Search Head/Indexer Cluster      
        for nArg in range(1, len(sys.argv)):
            strArgLC = sys.argv[nArg].lower()

            if (strArgLC == "-searchheadcluster"):
                bSearchHeadCluster = True
                #A Search Head Cluster will always have an independent Indexer
                bSeparateIndexer = True
                
            if (strArgLC == "-separateindexer"):
                bSeparateIndexer = True

        #In an Indexer Cluster, index has to be creating using the Master Node. For a Separate Indexer, the index shouldn't be created on this server
        if (not bSeparateIndexer):
            createPerseusEventsIndex()

        print (Perseus_Management_Log.PERSEUS_MANAGEMENT_OPERATION_STATUS_FIELD_NAME)
        print ("The Installation Completed Successfully")

        logPerseus.logPerseusInstallSuccess()

        #In a Search Head Cluster, this has to be set by the Deployer
        if (not bSearchHeadCluster):
            #Update the app.conf to indicate the app is now configured
            try:
                configApp = Splunk_Config.SplunkConfig("app")
                configApp.setConfigFileStanzaKeyValue("install", "is_configured", "1")
                
            #We just ignore if this fails
            except:
                pass

        sys.exit(0)  

    except Exception as err:
        
        strError = "An error was encountered during the install: " + str(err)
        
        print("Error Message")
        print (strError)

        logPerseus.logPerseusInstallFailure(strError)
        
        #!TFinish - OPTIONAL - We may want to undo anything we did or put in checks to prevent already existing errors if this has to be run multiple times. For the moment it shouldn't be an issue because there is no problem creating the lookup or index multiple times or 

        #Still return 0 to indicate script ran
        sys.exit(0)          
    
