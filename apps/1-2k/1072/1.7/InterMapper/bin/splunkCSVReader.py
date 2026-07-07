# InterMapper for Splunk App - class to read previously stored Splunk lookups

import logging
from imUtils import ImDevice, ImMap, logMethodEntry, logMethodExit, toUnicode, FILEPATHS
import sys
from cStringIO import StringIO
from csv import DictReader
import imGlobals

class SplunkCSVReader(object):
    appConfig = None
    sessionNo = None
    fileHandler = None
    logger = None
    scrRuntime = None
    
    def __init__(self, appConfig, fileHandler, sessionNo= -1, logLevel=logging.INFO, scrRuntime=False):
        self.appConfig = appConfig
        self.sessionNo = sessionNo
        self.fileHandler = fileHandler
        self.logger = logging.getLogger('splunk.apps.intermapper.splunkfilehandler')
        self.logger.setLevel(logLevel)
        self.scrRuntime = scrRuntime
    
    def readDeviceCSV(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        
        error = 0
        deviceDict = dict()
        
        deviceFile = self.fileHandler.accessPath(FILEPATHS['deviceCsv'], 'r')
        #deviceFile = codecs.open(FILEPATHS['deviceCsv'], 'r', encoding='utf-8-sig')
        if (deviceFile != None):
            tempString = deviceFile.read().encode('utf-8')
            memoryFile = StringIO(tempString)
            # DictReader can't read Unicode, so we must convert back to utf-8 before having DictReader look at the file
            # This method is a terrible hack
            try:
                reader = DictReader(memoryFile)
                for lineDict in reader:
                    try:
                        currentDevice = ImDevice()                            
                        if lineDict.has_key('mapid'):       #older deviceCSV does not have mapid column
                            currentDevice.mapId = toUnicode(lineDict['mapid'])
                        if lineDict.has_key('mapname'):       #older deviceCSV does not have mapid column
                            currentDevice.mapName = toUnicode(lineDict['mapname'])
                        currentDevice.deviceName = toUnicode(lineDict['label'])
                        currentDevice.deviceHost = toUnicode(lineDict['host'])
                        currentDevice.deviceSysName = toUnicode(lineDict['sysname'])
                        currentDevice.deviceNetBios = toUnicode(lineDict['netbiosname'])
                        currentDevice.deviceIP = toUnicode(lineDict['ip'])
                        currentDevice.deviceIMID = toUnicode(lineDict['deviceIMID'])
                        deviceDict[currentDevice.deviceIMID] = currentDevice
                        self.logger.debug("deviceIMID=\"%s\" name=\"%s\" host=\"%s\" ip=\"%s\" sysname=\"%s\" netbiosname=\"%s\" \n", currentDevice.deviceIMID, currentDevice.deviceName, currentDevice.deviceHost, currentDevice.deviceIP, currentDevice.deviceSysName, currentDevice.deviceNetBios)
                    except ValueError as e:
                        self.logger.error("sessionNo=\"%i\" action=\"Error Reading Device CSV\" message=\"%s\"", self.sessionNo, str(format(e)))
                    except KeyError as e:
                        self.logger.error("sessionNo=\"%i\" action=\"Error Reading Device CSV\" message=\"%s\"", self.sessionNo, str(format(e)))
            except IOError as e:
                self.logger.error("scriptName=\"%s\" self.sessionNo=\"%i\" action=\"Error Reading Device CSV\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
                error = 1
            finally:
                try:
                    deviceFile.close()
                except Exception as e:
                    self.logger.error("scriptName=\"%s\" self.sessionNo=\"%i\" action=\"Error Closing Device CSV\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
                memoryFile.close()
                
        if (error == 0):
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
            return 0, deviceDict
        else:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 1, 1    
 
    def readMapCSV(self):
        
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
               
        error = 0
        mapDict = dict()
        
        mapFile = self.fileHandler.accessPath(FILEPATHS['mapCsv'], 'r')
        if (mapFile != None):
            tempString = mapFile.read().encode('utf-8')
            memoryFile = StringIO(tempString)
            # DictReader can't read Unicode, so we must convert back to utf-8 before having DictReader look at the file
            # This method is a terrible hack
            try:
                reader = DictReader(memoryFile)
                for lineDict in reader:
                    try:
                        currentMap = ImMap()
                        currentMap.mapName = toUnicode(lineDict['mapname'])  
                        currentMap.mapId = toUnicode(lineDict['mapid'])
                        currentMap.mapLayer = toUnicode(lineDict['layer2'])
                        if currentMap.mapName == self.appConfig['defaultMapName']:
                            currentMap.defaultMap = True
                            imGlobals.globalMapId = currentMap.mapId
                            self.logger.debug("HP-DEBUG: readMapCSV(), globalMapId =\"%s\"\n", imGlobals.globalMapId)
                        else:
                            currentMap.defaultMap = False
                        mapDict[currentMap.mapId] = currentMap
                    except ValueError as e:
                        self.logger.error("sessionNo=\"%i\" action=\"Error Reading Map CSV\" message=\"%s\"", self.sessionNo, str(format(e)))
            except IOError as e:
                self.logger.error("scriptName=\"%s\" self.sessionNo=\"%i\" action=\"Error Reading Map CSV\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
                error = 1
            finally:
                try:
                    mapFile.close()
                except Exception:
                    self.logger.error("scriptName=\"%s\" self.sessionNo=\"%i\" action=\"Error Closing Map CSV\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
                memoryFile.close()
            
        if (error == 0):
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
            return 0, mapDict
        else:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 1, 1
        
    def readOldCSVs(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        
        deviceResult, deviceDict = self.readDeviceCSV()
        if deviceResult == 0:
            mapResult, mapDict = self.readMapCSV()
            if mapResult == 0:
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
                return 0, deviceDict, mapDict
            else:
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
                return 1, 1, 1
        else:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 1, 1, 1
 
## end class SplunkCSVReader
