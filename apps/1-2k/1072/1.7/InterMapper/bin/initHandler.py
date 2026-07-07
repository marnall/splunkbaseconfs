# InterMapper for Splunk App - class to handle scheduled script initialization and full dashboard regeneration

import logging
from imUtils import logMethodEntry, logMethodExit, getViews, splitExistingViews, restReloadViews, FILEPATHS
import time
from os.path import exists, getmtime, join, split
import ConfigParser
import __main__ as main

class SimpleInitHandler(object):
    sessionNo = None
    exitHandler = None
    fileHandler = None
    logger = None
    scrRuntime = None
        
    def __init__(self, exitHandler, fileHandler, sessionNo= -1, logLevel=logging.INFO, scrRuntime=False):
        self.sessionNo = sessionNo
        self.exitHandler = exitHandler
        self.fileHandler = fileHandler
        self.logger = logging.getLogger('splunk.apps.intermapper.inithandler')
        self.logger.setLevel(logLevel)
        self.scrRuntime = scrRuntime
        
    def handleFreshPid(self, pidPath):
        # Leave PID file, end this run of script
        self.logger.debug("sessionNo=\"%i\" action=\"Checking PID\" message=\"Leaving PID\" path=\"%s\"", self.sessionNo, pidPath)
        quit()
        
    def handleStalePid(self, pidPath):
        # Force removal of PID file, clear errors end this run of script
        self.logger.error("sessionNo=\"%i\" action=\"Checking PID\" message=\"Removing PID\" path=\"%s\"", self.sessionNo, pidPath)
        self.exitHandler.cleanExit()
        
    def handleNoPid(self, pidPath):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        self.logger.debug("sessionNo=\"%i\" action=\"Checking PID\" message=\"Creating PID file\" path=\"%s\"", self.sessionNo, pidPath)
        try:
            pidFile = open(pidPath, 'w')
        except IOError as e:
            self.logger.error("sessionNo=\"%i\" action=\"Creating PID\" message=\"Error: Unable to create PID\" path=\"%s\" error=\"%s\"", self.sessionNo, pidPath, str(format(e)))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
        except Exception as e:
            self.logger.error("sessionNo=\"%i\" action=\"Creating PID\" message=\"Error: Unexpected Error\" path=\"%s\" error=\"%s\"", self.sessionNo, pidPath, str(format(e)))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
        else:
            self.logger.info("sessionNo=\"%i\" action=\"Creating PID\" message=\"PID Created\" path=\"%s\"", self.sessionNo, pidPath)
            pidFile.write("1")
            pidFile.close()
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
    
    def checkPidAge(self, pidPath, freshAge, staleAge): #@UnusedVariable
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        if getmtime(pidPath) < (time.time() - freshAge):
            # pidFile is more than freshAge old, treat as stale
            self.logger.info("sessionNo=\"%i\" action=\"Checking PID\" message=\"Stale PID\" path=\"%s\"", self.sessionNo, pidPath)
            self.handleStalePid(pidPath)
        else:
            # pidFile is less than freshAge old, still fresh
            self.handleFreshPid(pidPath)
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
        
    def checkPid(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        pidName = split(main.__file__)[1] + '.pid'
        pidPath = join(FILEPATHS['pidDir'], pidName)
        if exists(pidPath):
            # pidFile exists
            self.checkPidAge(pidPath, 300, 600)
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
        else:
            # pidFile doesn't exist
            self.handleNoPid(pidPath)
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
    

class InitHandler(SimpleInitHandler):
    viewHandler = None
    configLoader = None
    sessionKey = None
        
    def __init__(self, exitHandler, fileHandler, viewHandler, configLoader, sessionKey=None, sessionNo= -1, logLevel=logging.INFO, scrRuntime=False):
        SimpleInitHandler.__init__(self, exitHandler, fileHandler, sessionNo, logLevel, scrRuntime)
        self.viewHandler = viewHandler
        self.configLoader = configLoader
        self.sessionKey = sessionKey
        
    # # Initialization and PID Functions ##
    
    def handleStalePid(self, pidPath):
        # Override base class method
        self.logger.error("sessionNo=\"%i\" action=\"Checking PID\" message=\"Forcing reload\" path=\"%s\"", self.sessionNo, pidPath)
        self.forceReload()
        
    def checkPidAge(self, pidPath, freshAge, staleAge):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        if getmtime(pidPath) < (time.time() - freshAge):
            # pidFile is more than freshAge old, check whether reload has been forced
            self.logger.info("sessionNo=\"%i\" action=\"Checking PID\" message=\"PID not fresh\" path=\"%s\"", self.sessionNo, pidPath)
            stateValues = self.configLoader.getStateValues()
            if (stateValues == 0 or stateValues == 1 or stateValues == 2):
                # error reading stateValues, force the reload
                self.logger.error("sessionNo=\"%i\" action=\"Checking PID\" message=\"Error checking state.conf, forcing reload\"", self.sessionNo)
                self.handleStalePid(pidPath)
            elif stateValues['forceReload'] == "1":
                # reload requested in state.conf
                self.logger.info("sessionNo=\"%i\" action=\"Checking PID\" message=\"Reload requested\"", self.sessionNo)
                self.handleStalePid(pidPath)
            elif getmtime(pidPath) < (time.time() - staleAge):
                # pidFile is more than staleAge old, just force a reload
                self.logger.info("sessionNo=\"%i\" action=\"Checking PID\" message=\"PID more than 10 min old, forcing reload\"", self.sessionNo)
                self.handleStalePid(pidPath)
            else:
                # pidFile is between freshAge and staleAge old, no reload forced, just exit
                self.logger.debug("sessionNo=\"%i\" action=\"Checking PID\" message=\"Exiting\"", self.sessionNo)
                self.handleFreshPid(pidPath)
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
        else:
            # pidFile is less than freshAge old, still fresh
            self.handleFreshPid(pidPath)
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
        
    # # End Initialization and PID Functions ##

    def forceReload(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
    
        mapsToDelete = []
        dashsToDelete = []
        existingViews = getViews(FILEPATHS, self.logger, self.sessionNo, self.scrRuntime)
        if existingViews:
            existingMaps, existingDashs = splitExistingViews(existingViews, self.logger, self.sessionNo, self.scrRuntime)
    
            for name in existingMaps:
                mapsToDelete.append(name)
    
            for name in existingDashs:
                dashsToDelete.append(name)
    
            if mapsToDelete:
                self.viewHandler.deleteMaps(mapsToDelete)
    
            if dashsToDelete:  
                self.viewHandler.deleteDashboards(dashsToDelete)
              
        # legacy - the md5 files are now unused
        devMd5Dest = FILEPATHS['deviceFileMd5']
        self.fileHandler.accessPath(devMd5Dest, 'd')
        mapMd5Dest = FILEPATHS['mapFileMd5']
        self.fileHandler.accessPath(mapMd5Dest, 'd')
        
        # Non-existent csvs cause Splunk errors 
        # assume that deviceCsv and mapCsv will be created on the next run of this script
        # that means that a blank portCsv must be created here
        # (blank deviceCsv or mapCsv files will probably cause readOldCSVs to error out)
        devTablePath = FILEPATHS['deviceCsv']
        self.fileHandler.accessPath(devTablePath, 'd')  
        mapTablePath = FILEPATHS['mapCsv']
        self.fileHandler.accessPath(mapTablePath, 'd')
        portTablePath = FILEPATHS['portCsv']
        self.fileHandler.accessPath(portTablePath, 'd')
        # open the portTable for appending (creates if doesn't exist)
        portTable = self.fileHandler.accessPath(portTablePath, 'ab')
        # add a header line then close the portTable if we managed to open it
        if (portTable != None):
            portTable.write("Port,Device IP,Device MAC,Switch,First Detected on Port,Last Detected on Port\n")
            portTable.close()
    
        localConf_fp = FILEPATHS['stateFile']
        localConfig = ConfigParser.ConfigParser()
        # force the content of the stateFile 
        # (so that we don't break trying to read a file with errors that we intend to overwrite anyway)
        #localConfig.read(localConf_fp)
        localConfig.add_section("state")
        localConfig.set("state", "forceReload", "0")
        configFile = self.fileHandler.accessPath(localConf_fp, "w")
        localConfig.write(configFile)
        if self.sessionKey != None:
            restReloadViews(self.sessionNo, self.sessionKey)
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
        self.exitHandler.cleanExit()
        
## End class InitHandler
