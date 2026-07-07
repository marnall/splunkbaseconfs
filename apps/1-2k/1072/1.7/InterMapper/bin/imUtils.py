# InterMapper for Splunk App - utility functions

import inspect
from urllib import quote
import time
import logging
import os
from os.path import dirname, join, abspath
from re import sub

### Define globals ###

rootLogger = logging.getLogger('splunk.apps.intermapper')

FILEPATHS = {"deviceCsv" : abspath(join(dirname(__file__), '..', 'lookups', 'deviceTable.csv')),
                     "mapCsv" : abspath(join(dirname(__file__), '..', 'lookups', 'mapTable.csv')),
                     "portCsv" : abspath(join(dirname(__file__), '..', 'lookups', 'switchPort.csv')),
                     "reloadFile" : abspath(join(dirname(__file__), '..', 'local', 'reloadFile')),
                     "outputHtml" : abspath(join(dirname(__file__), '..', 'appserver', 'static', '')),
                     "viewRoot" : abspath(join(dirname(__file__), '..', 'local', 'data', 'ui', 'views', '')),
                     "localDir" : abspath(join(dirname(__file__), '..', 'local', '')),
                     "defaultDir" : abspath(join(dirname(__file__), '..', 'default', '')),
                     "mapHtmlTemplate" : abspath(join(dirname(__file__), '..', 'default', 'maphtml.imtemp')),
                     "mapXmlTemplate" : abspath(join(dirname(__file__), '..', 'default', 'mapxml.imtemp')),
                     "deviceFileMd5" : abspath(join(dirname(__file__), '..', 'local', 'devices.md5')),
                     "mapFileMd5" : abspath(join(dirname(__file__), '..', 'local', 'maps.md5')),
                     "imageRoot" : abspath(join(dirname(__file__), '..', 'appserver', 'static', 'images', '')),
                     "pidDir" : abspath(join(dirname(__file__), '..', 'default', '')),
                     "errFile" : abspath(join(dirname(__file__), '..', 'default', 'imStatus.log')),
                     "settingsFile" : abspath(join(dirname(__file__), '..', 'local', 'settings.conf')),
                     "stateFile" : abspath(join(dirname(__file__), '..', 'local', 'state.conf')),
                     "appPath" : abspath(join(dirname(__file__), '..')),
                     "linkRoot" : "/en-US/app/InterMapper/"}

### End globals ###

class ImDevice(object):
    deviceName = None
    deviceProbe = None
    deviceHost = None
    deviceSysName = None
    deviceNetBios = None
    deviceIP = None
    deviceIMID = None
    mapId = None
    mapName = None
#    deviceTemplate = None
    _uniqueFN = None
    _xmlPath = None
    type = 'device'
        
    def _getUniqueFN(self):
        if (self._uniqueFN == None):
            uniqueString = (self.deviceName + u'.' + self.deviceIMID).encode('utf8')
            # quote most special characters
            uniqueString = quote(uniqueString, '')
            # .% remain to be quoted
            uniqueString = uniqueString.replace('.', '--')
            uniqueString = uniqueString.replace('%', '__')
            self._uniqueFN = uniqueString
        return self._uniqueFN
    def dashboardPath(self):
        if (self._xmlPath == None):
            self._xmlPath = "imdevice" + self.deviceIMID + ".xml"
        return self._xmlPath
    def __str__(self):
        strName = self.deviceName.encode('utf8') if self.deviceName != None else None
        strHost = self.deviceHost.encode('utf8') if self.deviceHost != None else None
        strSysName = self.deviceSysName.encode('utf8') if self.deviceSysName != None else None
        strNetBios = self.deviceNetBios.encode('utf8') if self.deviceNetBios != None else None
#        strTemplate = self.deviceTemplate.encode('utf8') if self.deviceTemplate != None else None
        strMapId = self.mapId.encode('utf8') if self.mapId != None else None
        strMapName = self.mapName.encode('utf8') if self.mapId != None else None
        return ('{ deviceName=\"' + strName
                + '\" deviceHost=\"' + strHost
                + '\" deviceSysName=\"' + strSysName
                + '\" deviceNetBios=\"' + strNetBios
                + '\" deviceIP=\"' + str(self.deviceIP)
                + '\" mapId=\"' + strMapId
                + '\" mapName=\"' + strMapName
                + '\" deviceIMID=\"' + str(self.deviceIMID)
              #                + '\" deviceTemplate=\"' + strTemplate 
                + '\" }')
    
class ImMap(object):
    mapName = None
    mapId = None
    mapLayer = None
    _uniqueFN = None
    _xmlPath = None
    _staticHtmlPath = None
    _htmlPath = None
    _mapImage = None
    _mapBgImage = None
    type = 'map'

#    def __init__(self, mapName, mapId, mapLayer):
#        self.mapName = mapName
#        self.mapId = mapId
#        self.mapLayer = mapLayer
    
    def _getUniqueFN(self):
        if (self._uniqueFN == None):
            uniqueString = (self.mapName + u'.' + self.mapId).encode('utf8')
            # quote most special characters
            uniqueString = quote(uniqueString, '')
            # .% remain to be quoted
            uniqueString = uniqueString.replace('.', '--')
            uniqueString = uniqueString.replace('%', '__')
            self._uniqueFN = uniqueString
        return self._uniqueFN
    def xmlPath(self):
        if (self._xmlPath == None):
            self._xmlPath = "immap" + self._getUniqueFN() + ".xml"
        return self._xmlPath
    def staticHtmlPath(self):
        if (self._staticHtmlPath == None):
            self._staticHtmlPath = "imstatic" + self._getUniqueFN() + ".html"
        return self._staticHtmlPath
    def htmlPath(self):
        if (self._htmlPath == None):
            self._htmlPath = "immap" + self._getUniqueFN() + ".html"
        return self._htmlPath
    def mapImage(self):
        if (self._mapImage == None):
            self._mapImage = self._getUniqueFN() + ".png"
        return self._mapImage
    def mapBgImage(self):
        if (self._mapBgImage == None):
            self._mapBgImage = self._getUniqueFN() + "bg.png"
        return self._mapBgImage

    defaultMap = False
    bgImage = False
    bgTop = None
    bgLeft = None
    def __str__(self):
        strName = self.mapName.encode('utf8') if self.mapName != None else None
        return ('{ mapName=\"' + strName
                + '\" mapId=\"' + str(self.mapId) 
                + '\" mapLayer=\"' + str(self.mapLayer)
                + '\" defaultMap=\"' + str(self.defaultMap)
                + '\" bgImage=\"' + str(self.bgImage)
                + '\" bgTop=\"' + str(self.bgTop)
                + '\" bgLeft=\"' + str(self.bgLeft) + '\" }')
        
def mapXMLPathToImMap(xmlpath):
    imMap = ImMap()
    imMap._uniqueFN = xmlpath[5:-4]
    return imMap

# # Utility Functions ##

def returnFunction():
    return inspect.stack()[1][3]

def returnParent():
    return inspect.stack()[2][3]

def returnGrandparent():
    return inspect.stack()[3][3]

def toUnicode(obj, encoding='utf8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
        return obj

def logMethodEntry(logger, sessionNo= -1, scrRuntime=False):
    start_time = 0
    if scrRuntime:
        start_time = time.time()
    logger.debug("sessionNo=\"%i\" action=\"Method Entry\" currentFunction=\"%s\" parentFunction=\"%s\"", sessionNo, returnParent(), returnGrandparent())
    return start_time

def logMethodExit(start_time, logger, sessionNo= -1, scrRuntime=False, status='Normal'):
    if scrRuntime:
        runTime = time.time() - start_time
        logger.info("sessionNo=\"%i\" runTime=\"%s\" function=\"%s\"", sessionNo, runTime, returnParent())
    if status != 'Normal':
        logger.debug("sessionNo=\"%i\" action=\"Method Exit\" currentFunction=\"%s\" parentFunction=\"%s\" status=\"%s\"", sessionNo, returnParent(), returnGrandparent(), status)

def escapeApos(string):
    subbed = sub("'", "&apos;", string)
    subbed = sub('"', "&quot;", subbed)
    return subbed

# # End of Utility Functions ##

# # Splunk-local Functions ##

def restReloadViews(sessionNo, sessionKey):
    import splunk.rest #@UnresolvedImport
    rootLogger.debug("sessionNo=\"%i\" action=\"Reloading Splunk Views\" sessionKey=\"%s\"", sessionNo, str(sessionKey))
    splunk.rest.simpleRequest("/servicesNS/nobody/InterMapper/data/ui/views/_reload", sessionKey=sessionKey)
    rootLogger.info("sessionNo=\"%i\" action=\"Reloading Splunk Views\" message=SUCCESS", sessionNo)

### Loading Functions ### 

def getViews(filePaths, logger, sessionNo= -1, scrRuntime=False):
    start_time = logMethodEntry(logger, sessionNo, scrRuntime)
  
    existingViews = []
    for _, _, filenames in os.walk(filePaths['viewRoot']): #dirpath, dirnames, filenames
        for name in filenames:
            existingViews.append(name)
    
    logMethodExit(start_time, logger, sessionNo, scrRuntime)
    return existingViews

def splitExistingViews(existingViews, logger, sessionNo= -1, scrRuntime=False):
    start_time = logMethodEntry(logger, sessionNo, scrRuntime)
    
    existingDashs = []
    existingMaps = []

    for name in existingViews:
        if name.find("imdevice") > -1:
            existingDashs.append(name)
        elif name.find("immap") > -1:
            existingMaps.append(name)

    logMethodExit(start_time, logger, sessionNo, scrRuntime)
    return existingMaps, existingDashs

# # End Splunk-local Functions ##
