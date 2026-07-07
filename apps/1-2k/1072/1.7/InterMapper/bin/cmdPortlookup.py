#!/usr/bin/python -tt
#
# InterMapper for Splunk App - Script to download switchPort.csv

import os
from os.path import dirname, join
import logging #@UnusedImport
import logging.handlers
import random
from urllib2 import HTTPError
from connector import HTTPConnector
from exitHandler import ExitHandler
from splunkFileHandler import SplunkFileHandler
from splunkConfigLoader import SplunkConfigLoader
from initHandler import SimpleInitHandler

sessionNo = random.randint(1, 2000)

# Set up logging
logger = logging.getLogger('splunk.apps.intermapper')
logLevel = logging.INFO
logger.setLevel(logLevel)
handler = logging.handlers.RotatingFileHandler(filename=os.path.join(dirname(__file__), '..', 'local', 'imPort.log'), mode='a', maxBytes=1000000, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s log_level=%(levelname)s %(message)s'))
logger.addHandler(handler)

try:
    exitHandler = ExitHandler(sessionNo, logLevel)
    fileHandler = SplunkFileHandler(exitHandler, sessionNo, logLevel)
    initHandler = SimpleInitHandler(exitHandler, fileHandler, sessionNo, logLevel)
    initHandler.checkPid()
    
    configLoader = SplunkConfigLoader(fileHandler, sessionNo, logLevel)
    configValues = configLoader.loadConfig()
    
    
    if (configValues != 0 and configValues != 1 and configValues != 2):
        # if config correctly read, continue    
        outputName = join(dirname(__file__), '..', 'lookups', 'switchPort.csv')
        portOrNone = configValues.get('serverPort')
        authOrNone = configValues.get('auth')
        httpConnector = HTTPConnector(host=configValues['serverUrl'], port=portOrNone, https=configValues['sslRequired'], auth=authOrNone, logLevel=logLevel)
            
        # Try downloading switchPort.csv file
        try:
            urlObject = httpConnector.getURL('~files/extensions/com.dartware.switches/switchPort.csv', 'GETting switchPort.csv')
            # file found as expected, read then write to targetFile
            switchCsv = urlObject.read()
            targetFile = fileHandler.accessPath(outputName, 'w')
            if targetFile:
                targetFile.write(switchCsv)
                targetFile.close()
                # log success after completion
                ##logger.info("sessionNo=\"%i\" action=\"SwitchPort Poll\" message=\"Success\"", sessionNo)
            else:
                logger.error("sessionNo=\"%i\" action=\"SwitchPort Poll\" message=\"Could not open switchPort.csv for writing\"", sessionNo)
        except HTTPError as e:
            # server returned a bad response, log error
            logger.error("sessionNo=\"%i\" action=\"SwitchPort Poll\" message=\"Bad server response\" error=\"%s\"", sessionNo, str(e.code))
        except IOError as e:
            logger.error("sessionNo=\"%i\" action=\"SwitchPort Poll\" message=\"IOError\" error=\"%s\"", sessionNo, str(format(e)))
        
    else:
        # otherwise log error
        logger.error("sessionNo=\"%i\" action=\"SwitchPort Poll\" message=\"Settings error, aborting.\"", sessionNo)
    
    #endif
    exitHandler.cleanExit()

# Emergency catch block for dump to log        
except Exception, e:
    import traceback
    stack = traceback.format_exc()
    logging.critical("sessionNo=\"%i\" action=\"SwitchPort Poll\" message=\"Fatal Error '%s'.\" traceback=\"%s\"" % (sessionNo, e, stack))
