# InterMapper for Splunk App - main function to download image and coordinate data for a single map

from os.path import join, dirname
import logging #@UnusedImport
import logging.handlers
import random
import imGlobals
from imUtils import logMethodEntry, logMethodExit
from webExitHandler import WebExitHandler, LoadMapException
from imDownloader import ImDownloader
from splunkConfigLoader import SplunkConfigLoader
from splunkCSVReader import SplunkCSVReader
from splunkFileHandler import SplunkFileHandler
from splunkViewHandler import SplunkViewHandler

############# Enable debug mode below #############
debug = 0
###################################################
######## Enable runTime counter mode below ########
scrRuntime = 0
###################################################

# set up logging
if debug:
    globalLogLevel = logging.DEBUG
    globalLogFileName = join(dirname(__file__), '..', 'local', 'imSingleDebugLog.log')   
else:
    globalLogLevel = logging.INFO
    globalLogFileName = join(dirname(__file__), '..', 'local', 'imSingleAppLog.log')

rootLogger = logging.getLogger('splunk.apps.intermapper')
rootLogger.setLevel(globalLogLevel)
handler = logging.handlers.RotatingFileHandler(filename=globalLogFileName, mode='a', maxBytes=1000000, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s log_level=%(levelname)s %(message)s'))
rootLogger.addHandler(handler)

sessionKey = None  

def loadMap(mapId):
    try:
        # choose a sessionNo
        sessionNo = random.randint(1, 2000)
        
        start_time = logMethodEntry(rootLogger, sessionNo, scrRuntime)
    
        exitHandler = WebExitHandler(sessionNo, globalLogLevel)
        fileHandler = SplunkFileHandler(exitHandler, sessionNo, globalLogLevel)
        configLoader = SplunkConfigLoader(fileHandler, sessionNo, globalLogLevel)
        viewHandler = SplunkViewHandler(exitHandler, fileHandler, sessionKey, sessionNo, globalLogLevel)
        
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
            error, deviceDict, mapDict = csvReader.readOldCSVs()
            if error:
                rootLogger.error("sessionNo=\"%i\" action=\"Read Splunk CSVs\" message=\"Error\"", sessionNo)
            else:
                downloader = ImDownloader(appConfig, exitHandler, fileHandler, viewHandler, sessionKey, sessionNo)
                downloader.downloadMap(mapId, mapDict, deviceDict)
    
        imGlobals.globalMapId = mapId
        rootLogger.debug("HP-DEBUG: switched to mapId=\"%d\"", imGlobals.globalMapId)
        logMethodExit(start_time, rootLogger, sessionNo, scrRuntime)
        
    except LoadMapException, e:
        # This exception will be raised if anything calls the "crashOut" function in the WebExitHandler
        # This error isn't unexpected, so we handle it separately to the next catch-all block
        # We should re-raise it so that the mako html template can display an error
        raise
    except Exception, e:
        import traceback
        stack = traceback.format_exc()
        rootLogger.critical("sessionNo=\"%i\" action=\"Fatal Error '%s'.\" traceback=\"%s\"" % (sessionNo, e, stack))
        # We should raise a LoadMapException so that the mako html template can display an error
        raise LoadMapException()
		

#
#if __name__ == '__main__':
#    loadMap('g55d8098f')
