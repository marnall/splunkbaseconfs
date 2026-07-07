#!/usr/bin/python -tt
#
# InterMapper for Splunk App - Scheduled app script to download InterMapper map and device data
#                              and output it as Splunk dashboards and lookups

import sys
from os.path import join, dirname
import logging #@UnusedImport
import logging.handlers
import random
from imUtils import logMethodEntry, logMethodExit
from exitHandler import ExitHandler
from imDownloader import ImDownloader
from initHandler import InitHandler
from splunkConfigLoader import SplunkConfigLoader
from splunkCSVReader import SplunkCSVReader
from splunkFileHandler import SplunkFileHandler
from splunkViewHandler import SplunkViewHandler

###################################################
########## Enable independent mode below ##########
independent = 0
###################################################
############# Enable debug mode below #############
debug = True
###################################################
######## Enable runTime counter mode below ########
scrRuntime = 0
###################################################

# choose a sessionNo
sessionNo = random.randint(1, 2000)

# set up logging
if debug:
    globalLogLevel = logging.DEBUG
    globalLogFileName = join(dirname(__file__), '..', 'local', 'imDebugLog.log')   
else:
    globalLogLevel = logging.INFO
    globalLogFileName = join(dirname(__file__), '..', 'local', 'imAppLog.log')

rootLogger = logging.getLogger('splunk.apps.intermapper')
rootLogger.setLevel(globalLogLevel)
handler = logging.handlers.RotatingFileHandler(filename=globalLogFileName, mode='a', maxBytes=1000000, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s log_level=%(levelname)s %(message)s'))
rootLogger.addHandler(handler)

# extra init if run from Splunk
if independent == 0:
    sessionKey = sys.stdin.read().strip()
    rootLogger.debug("sessionNo=\"%i\" sessionKey=\"%s\"", sessionNo, str(sessionKey))
else:
    sessionKey = None  
        
def main():
    try:
        start_time = logMethodEntry(rootLogger, sessionNo, scrRuntime)
    
        exitHandler = ExitHandler(sessionNo, globalLogLevel)
        fileHandler = SplunkFileHandler(exitHandler, sessionNo, globalLogLevel)
        configLoader = SplunkConfigLoader(fileHandler, sessionNo, globalLogLevel)
        viewHandler = SplunkViewHandler(exitHandler, fileHandler, sessionKey, sessionNo, globalLogLevel)
        initHandler = InitHandler(exitHandler, fileHandler, viewHandler, configLoader, sessionKey, sessionNo, globalLogLevel)

        initHandler.checkPid()
        
        ## Check whether reload required
        stateConfig = configLoader.getStateValues()
        if stateConfig == 0:
            exitHandler.fatalErrorHandler(error="sectionError", errorMessage="0")
        elif stateConfig == 1:
            exitHandler.fatalErrorHandler(error="optionError", errorMessage="0")
        elif stateConfig == 2:
            exitHandler.fatalErrorHandler(error="emptyValue", errorMessage="0")
        else:
            rootLogger.info("sessionNo=\"%i\" action=\"State Loaded\" message=\"Success\"", sessionNo)
            if stateConfig['forceReload'] == "1":
                initHandler.forceReload()
                ## This will cause the script to exit
        
        appConfig = configLoader.loadConfig()
        if appConfig == 0:
            exitHandler.fatalErrorHandler(error="sectionError", errorMessage="0")
        elif appConfig == 1:
            exitHandler.fatalErrorHandler(error="optionError", errorMessage="0")
        elif appConfig == 2:
            exitHandler.fatalErrorHandler(error="emptyValue", errorMessage="0")
        else:
            rootLogger.info("sessionNo=\"%i\" action=\"Configuration Loaded\" message=\"Success\"", sessionNo)
            csvReader = SplunkCSVReader(appConfig, fileHandler, sessionNo, globalLogLevel)
            result, oldDevXml, oldMapXml = csvReader.readOldCSVs()
            if result:
                rootLogger.error("sessionNo=\"%i\" action=\"Read Splunk CSVs\" message=\"Error\"", sessionNo)
            else:
                downloader = ImDownloader(appConfig, exitHandler, fileHandler, viewHandler, sessionKey, sessionNo)
                downloader.testConfig()
                result = downloader.getImData(oldDevXml, oldMapXml)
                if result:
                    rootLogger.error("sessionNo=\"%i\" action=\"Download Intermapper data\" message=\"Cannot reach Intermapper server\"", sessionNo)
    
        logMethodExit(start_time, rootLogger, sessionNo, scrRuntime)
        exitHandler.cleanExit()
        
    except Exception, e:
        import traceback
        stack = traceback.format_exc()
        rootLogger.critical("sessionNo=\"%i\" action=\"Fatal Error '%s'.\" traceback=\"%s\"" % (sessionNo, e, stack))
        
if __name__ == '__main__':
    main()
