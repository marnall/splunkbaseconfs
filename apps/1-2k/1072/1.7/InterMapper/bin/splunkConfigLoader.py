# InterMapper for Splunk App - class to handle loading configuration data

import logging
from imUtils import logMethodEntry, logMethodExit, FILEPATHS
import ConfigParser
import sys

class SplunkConfigLoader(object):
    sessionNo = None
    fileHandler = None
    logger = None
    scrRuntime = None
    
    def __init__(self, fileHandler, sessionNo= -1, logLevel=logging.INFO, scrRuntime=False):
        self.sessionNo = sessionNo
        self.fileHandler = fileHandler
        self.logger = logging.getLogger('splunk.apps.intermapper.splunkconfigloader')
        self.logger.setLevel(logLevel)
        self.scrRuntime = scrRuntime
        
    def getStateValues(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        
        localSectionError = 0
        localOptionError = 0
        emptyValues = 0
        
        stateValues = {"forceReload" : "0"}
    
        localConf_fp = FILEPATHS['stateFile']
        localConfig = ConfigParser.ConfigParser()
        conf = self.fileHandler.accessPath(localConf_fp, 'r')
        if (conf != None):
            localConfig.readfp(conf)
        else:
            # state.conf doesn't exist yet, so create it and return our default
            outFile = self.fileHandler.accessPath(localConf_fp, 'w')
            outFile.write('[state]\nforceReload = 0')
            return stateValues
        #localConfig.read(localConf_fp)
    
        for name in stateValues:
            try:
                stateValues[name] = localConfig.get("state", name)
            except ConfigParser.NoSectionError as e:
                self.logger.error("scriptName=\"%s\" sessionNo=\"%i\" action=\"Reading Local Settings\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
                localSectionError = localSectionError + 1
            except ConfigParser.NoOptionError as e:
                self.logger.error("scriptName=\"%s\" sessionNo=\"%i\" action=\"Reading Local Settings\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
                localOptionError = localOptionError + 1
            else:
                if stateValues[name] == "":
                    emptyValues = emptyValues + 1
        
        if localSectionError > 0:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 0
        elif localOptionError > 0:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 1
        elif emptyValues > 0:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 2
        else:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
            return stateValues
                    
    
    def loadConfig(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        
        requiredValues = ["defaultMapName", "serverUrl", "sslRequired"]
        optionalValues = ["serverPort", "auth", "timeoutInSeconds"]
        configValues = {}
        localSectionError = 0
        localOptionError = 0
        emptyValues = 0
    
        localConf_fp = FILEPATHS['settingsFile']
        localConfig = ConfigParser.ConfigParser()
        conf = self.fileHandler.accessPath(localConf_fp, 'r')
        if (conf != None):
            localConfig.readfp(conf)
        #localConfig.read(localConf_fp)
    
        for name in requiredValues:
            try:
                configValues[name] = localConfig.get("imsettings", name)
            except ConfigParser.NoSectionError as e:
                self.logger.error("scriptName=\"%s\" sessionNo=\"%i\" action=\"Reading Local Settings\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
                localSectionError = localSectionError + 1
            except ConfigParser.NoOptionError as e:
                self.logger.error("scriptName=\"%s\" sessionNo=\"%i\" action=\"Reading Local Settings\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
                localOptionError = localOptionError + 1
            else:
                if configValues[name] == "":
                    emptyValues = emptyValues + 1
        
        for name in optionalValues:
            try:
                configValues[name] = localConfig.get("imsettings", name)
            except ConfigParser.NoSectionError as e:
                self.logger.debug("scriptName=\"%s\" sessionNo=\"%i\" action=\"Reading Local Settings\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
            except ConfigParser.NoOptionError as e:
                self.logger.debug("scriptName=\"%s\" sessionNo=\"%i\" action=\"Reading Local Settings\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
            else:
                if configValues[name] == "":
                    del configValues[name] # only keep optional config values if they're non-blank
    
        if localSectionError > 0:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 0
        elif localOptionError > 0:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 1
        elif emptyValues > 0:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 2
        else:
            sslReqString = configValues['sslRequired']
            if sslReqString == "1" or sslReqString == "t" or sslReqString == "T":
                configValues['sslRequired'] = True
            else:
                configValues['sslRequired'] = False
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
            return configValues

## End class SplunkConfigLoader
