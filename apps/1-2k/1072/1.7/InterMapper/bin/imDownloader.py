# InterMapper for Splunk App - class to handle downloading and parsing InterMapper data

import logging
from imUtils import ImDevice, ImMap, logMethodEntry, logMethodExit, getViews, splitExistingViews, restReloadViews, toUnicode, FILEPATHS
from connector import HTTPConnector
from urllib2 import HTTPError
from os.path import join
import re
import sys
import HTMLParser
from time import ctime
from xml.sax.saxutils import escape
import imGlobals
from splunkCSVReader import SplunkCSVReader

#global: used only in this module
imappNameParam = "client=imsplunk-1.7"      # change this when we change version of InterMapper for Splunk

class ImDownloader(object):
    sessionNo = None
    appConfig = None
    exitHandler = None
    fileHandler = None
    viewHandler = None
    httpConnector = None
    logger = None
    scrRuntime = None
    sessionKey = None
    logLevel = None
    timeoutInSeconds = None
	      
    def __init__(self, appConfig, exitHandler, fileHandler, viewHandler, sessionKey=None, sessionNo= -1, logLevel=logging.INFO, scrRuntime=False):
        self.sessionNo = sessionNo
        self.appConfig = appConfig
        self.exitHandler = exitHandler
        self.fileHandler = fileHandler
        self.viewHandler = viewHandler
        self.logger = logging.getLogger('splunk.apps.intermapper.imdownloader')
        self.logger.setLevel(logLevel)
        self.logLevel = logLevel
        self.scrRuntime = scrRuntime
        self.sessionKey = sessionKey       
        portOrNone = self.appConfig.get('serverPort')
        authOrNone = self.appConfig.get('auth')
        self.httpConnector = HTTPConnector(host=self.appConfig['serverUrl'], port=portOrNone, https=self.appConfig['sslRequired'], auth=authOrNone, logLevel=logLevel)     
        self.timeoutInSeconds = self.appConfig.get('timeoutInSeconds')
		
    # # Main App Logic ##
    
    def getImData(self, oldDevXml, oldMapXml):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
    
        result, deviceXml, mapXml = self.downloadXML()
        if result:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 1

        #self.downloadMaps(mapXml, deviceXml)
      
        existingViews = getViews(FILEPATHS, self.logger, self.sessionNo, self.scrRuntime)
        if existingViews:
            existingMaps, existingDashs = splitExistingViews(existingViews, self.logger, self.sessionNo, self.scrRuntime)
        else:
            existingMaps, existingDashs = [], []
            
#        # download map html the first time
#        if existingMaps == []:
#            self.downloadMaps(mapXml, deviceXml)
      
        self.viewHandler.cleanUpDashboards(deviceXml, existingDashs, oldDevXml)
        self.viewHandler.cleanUpMaps(mapXml, existingMaps, oldMapXml)
    
        if self.sessionKey != None:
            restReloadViews(self.sessionNo, self.sessionKey)
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
    
    # # End Main App Logic ##
    
    def refreshDeviceDashboards(self, oldDevXml, newDevXml):
        
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
          
        existingViews = getViews(FILEPATHS, self.logger, self.sessionNo, self.scrRuntime)
        if existingViews:
            existingMaps, existingDashs = splitExistingViews(existingViews, self.logger, self.sessionNo, self.scrRuntime)
        else:
            existingMaps, existingDashs = [], []
            
#        # download map html the first time
#        if existingMaps == []:
#            self.downloadMaps(mapXml, deviceXml)
      
        self.viewHandler.cleanUpDashboards(newDevXml, existingDashs, oldDevXml)        
        if self.sessionKey != None:
            restReloadViews(self.sessionNo, self.sessionKey)
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
        
    def testConfig(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)  
    
        devicesXMLFields_testing = "name,mapid"
        otherParams = imappNameParam + "&maxcount=5"
        try:
            # for testing only, we don't need to pass all the fields
            self.httpConnector.getTable('devices.xml', devicesXMLFields_testing, otherParams)
        except HTTPError as e:
            self.logger.error("sessionNo=\"%i\" action=\"Testing connection to Intermapper server - %s\" message=FAILED error=\"%s\"", self.sessionNo, self.httpConnector.serverBaseURL, str(e.code))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
            self.exitHandler.fatalErrorHandler(error="connError", errorMessage=str(format(e)))
        except IOError as e:
            self.logger.error("sessionNo=\"%i\" action=\"Testing connection to Intermapper server - %s\" message=FAILED error=\"%s\"", self.sessionNo, self.httpConnector.serverBaseURL, str(format(e)))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
            self.exitHandler.fatalErrorHandler(error="connError", errorMessage=str(format(e)))
        except Exception as e:
            self.logger.error("sessionNo=\"%i\" action=\"Testing connection to Intermapper server - %s\" message=FAILED error=\"%s\"", self.sessionNo, self.httpConnector.serverBaseURL, str(format(e)))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
            self.exitHandler.fatalErrorHandler(error="connError", errorMessage=str(format(e)))  
        else:
            self.logger.info("sessionNo=\"%i\" action=\"Testing connection to Intermapper server - %s\" message=PASSED", self.sessionNo, self.httpConnector.serverBaseURL)
            
        try:
            # for testing only, we don't need to pass all the fields
            self.httpConnector.getTable('devices.xml', devicesXMLFields_testing, otherParams)
        except HTTPError as e:
            self.logger.error("sessionNo=\"%i\" action=\"Testing follow-up connection to Intermapper server - %s\" message=FAILED error=\"%s\"", self.sessionNo, self.httpConnector.serverBaseURL, str(e.code))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
            self.exitHandler.fatalErrorHandler(error="connErrorTwo", errorMessage=str(format(e)))
        except IOError as e:
            self.logger.error("sessionNo=\"%i\" action=\"Testing follow-up connection to Intermapper server - %s\" message=FAILED error=\"%s\"", self.sessionNo, self.httpConnector.serverBaseURL, str(format(e)))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
            self.exitHandler.fatalErrorHandler(error="connErrorTwo", errorMessage=str(format(e)))
        else:
            self.logger.info("sessionNo=\"%i\" action=\"Testing follow-up connection to Intermapper server - %s\" message=PASSED", self.sessionNo, self.httpConnector.serverBaseURL)
      
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
        
    ### IM-side loading ###
    
    def downloadMapXML(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        
        mapDict = dict()
        mapInfo = []
    
        h = HTMLParser.HTMLParser()
        mapFields = 'mapid,mapname,layer2'      
        try:
            rawMapList = self.httpConnector.getTable('maps.xml', mapFields, imappNameParam).read()
        except HTTPError as e:
            self.logger.error("scriptName=\"%s\" self.sessionNo=\"%i\" action=\"Intermapper Server Connection Error - Map XML\" message=\"HTTP Error %s\"", sys.argv[0], self.sessionNo, str(e.code))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 1, 1
        except IOError as e:
            self.logger.error("scriptName=\"%s\" self.sessionNo=\"%i\" action=\"Intermapper Server Connection Error - Map XML\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 1, 1
        
        try:
            mapParseList = rawMapList.decode('iso-8859-1')
            
            #    mapLines = mapParseList.splitlines()
            #    mapList = []
            #    for mapLine in mapLines:
            #        mapList.append(mapLine.split(','))
            mapList = re.findall(r'<mapid>(g\w{8})</mapid>[^<]+<mapname>([^<]+)</mapname>[^<]+<layer2>([^<]+)</layer2>', mapParseList)
          
            for extracted_data in mapList:
                (mid, mn, ml) = extracted_data
                mapId = toUnicode(h.unescape(mn))
                if mapId and ("DetectionMap" not in mapId):  # have to filter out 'DetectionMap': new IM Server will not send this, but older IM Server will send
                    currentMap = ImMap()
                    currentMap.mapName = mapId
                    currentMap.mapId = toUnicode(h.unescape(mid))
                    currentMap.mapLayer = toUnicode(h.unescape(ml))
                    if self.logLevel == logging.DEBUG:
                        print("Currently working map = " + currentMap.mapName.encode('utf8'))
                    if currentMap.mapName == self.appConfig['defaultMapName']:
                        if self.logLevel == logging.DEBUG:
                            print("DEFAULT MAP = " + currentMap.mapName.encode('utf8'))
                        currentMap.defaultMap = True
                        imGlobals.globalMapId = currentMap.mapId
                    else:
                        currentMap.defaultMap = False
                    mapInfo.append("\"" + currentMap.mapName + "\",\"" + currentMap.mapId + "\",\"" + currentMap.mapLayer + "\"\n")
                    mapDict[currentMap.mapId] = currentMap
        except Exception as e:
            self.logger.critical("scriptName=\"%s\" self.sessionNo=\"%i\" action=\"Map XML Parse Error\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
            raise
      
        mapCsvOutput = 'mapname,mapid,layer2\n' + ''.join(mapInfo) + '\n'
        fileOut = open(FILEPATHS['mapCsv'], 'wb') # b to enforce unix newlines
        fileOut.write(mapCsvOutput.encode('utf8'))
        fileOut.close()
      
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
        return 0, mapDict
    
    def downloadDeviceXML(self, mapDict):      
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)        
        localMapId = imGlobals.globalMapId
        self.logger.debug("HP-DEBUG: downloadDeviceXML(), globalMapId =\"%s\"\n", localMapId)
            
        deviceDict = dict()
        deviceInfo = []         #list of devices of the given map
        
        h = HTMLParser.HTMLParser()
        devFields = 'name,probe,address,DNSName,SysName,NetBIOSName,IMID,id,vertexId,mapid,StatusLevel,Status'        
        try:
            rawDevList = self.httpConnector.getTable('devices.xml', devFields, imappNameParam).read()
        except HTTPError as e:
            self.logger.error("scriptName=\"%s\" self.sessionNo=\"%i\" action=\"Intermapper Server Connection Error - Device XML\" message=\"HTTP Error %s\"", sys.argv[0], self.sessionNo, str(e.code))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 1, 1
        except IOError as e:
            self.logger.error("scriptName=\"%s\" self.sessionNo=\"%i\" action=\"Intermapper Server Connection Error - Device XML\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 1, 1
        
        try:
            devParseList = rawDevList.decode('iso-8859-1')
            
            # add the comment "uc" to all devices without a comment
#            devParseList = re.sub(r'(<comment></comment>)', '<comment>uc</comment>', devParseList)
      
            #    devLines = devParseList.splitlines()
            #    deviceList = []
            #    for devLine in devLines:
            #        deviceList.append(devLine.split(','))
            
            # dictionary for all probe groups
            devGroupList = dict()
            
            deviceList = re.findall(r'<name>([^<]+)</name>[^<]+<probe>([^<]+)</probe>[^<]+<address>([^<]+)</address>[^<]+<DNSName>([^<]*)</DNSName>[^<]+<SysName>([^<]*)</SysName>[^<]+<NetBIOSName>([^<]*)</NetBIOSName>[^<]+<IMID>([\w]{2}[\w]{4}[\w]{4}d)</IMID>[^<]+<id>([^<]+)</id>[^<]+<vertexId>([^<]+)</vertexId>[^<]+[^<]+<mapid>(g\w{8})</mapid>[^<]+<StatusLevel>([^<]+)</StatusLevel>', devParseList)
      
            # first pass through data to create group dictionary
            for extracted_data in deviceList:
                (name, probe, ip, dns, sysname, netbios, imid, id, vertexid, mn, stslevel) = extracted_data            #@UnusedVariable
                #if we can find the map object
                name = h.unescape(name)
                if " " in name:
                    name = name.strip() # Removing leading and trailing spaces
                # if probe name is "probe group", place in group dict
                if probe == "Probe Group":
                    devGroupList[id] = toUnicode(name)
	  
            for extracted_data in deviceList:
            
                (name, probe, ip, dns, sysname, netbios, imid, id, vertexid, mn, stslevel) = extracted_data            #@UnusedVariable
                
                mapId = toUnicode(h.unescape(mn))                    
                if ("DetectionMap" not in mapId) and (mapDict==None or mapDict.has_key(mapId)):   # Must be a legit device that belongs to a map
                    mapObj = mapDict[mapId]
                    if mapObj:                  #if we can find the map object
                        name = h.unescape(name)
                        if " " in name:
                            name = name.strip() # Removing leading and trailing spaces
                        
                        currentDevice = ImDevice()
                        currentDevice.deviceName = toUnicode(name)
                        # if vertexId exists in the group dict, prepend the name from there
                        if devGroupList.has_key(vertexid) and probe != "Probe Group":
                            currentDevice.deviceName = devGroupList[vertexid] + u'/' + toUnicode(name)
                        else:
                            currentDevice.deviceName = toUnicode(name)
                            # if probe name is "probe group", place in group dict
                            #if probe == "Probe Group":
                                #devGroupList[id] = currentDevice.deviceName
                        currentDevice.deviceProbe = toUnicode(probe)
                        currentDevice.mapName = mapObj.mapName
                        currentDevice.deviceHost = toUnicode(h.unescape(dns))
                        currentDevice.deviceSysName = toUnicode(h.unescape(sysname))
                        currentDevice.deviceNetBios = toUnicode(h.unescape(netbios))
                        currentDevice.deviceIP = toUnicode(h.unescape(ip))
                        currentDevice.mapId = mapId
                        currentDevice.deviceIMID = toUnicode(h.unescape(imid))
                        statusLevel =  toUnicode(stslevel)
                        deviceInfo.append(currentDevice.deviceIMID + ",\"" + currentDevice.deviceName + "\"," + currentDevice.deviceProbe + "," + currentDevice.deviceIP + "," + currentDevice.deviceHost + ",\"" + currentDevice.mapName + "\",\"" + currentDevice.deviceSysName + "\"," + currentDevice.deviceNetBios + "," + statusLevel + "\n")
                        deviceDict[currentDevice.deviceIMID] = currentDevice
                    else:
                        self.logger.debug("HP-DEBUG: found mapId=\"%s\" has no map object", mapId)
                
#            print deviceCount

        except Exception as e:
            self.logger.critical("scriptName=\"%s\" self.sessionNo=\"%i\" action=\"Device XML Parse Error\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
            raise    

        devCsvOutput = 'deviceIMID,label,probe,ip,host,mapname,sysname,netbiosname,notification_level\n' + ''.join(deviceInfo) + '\n'

        fileOut = open(FILEPATHS['deviceCsv'], 'wb') # b to enforce unix newlines
        fileOut.write(devCsvOutput.encode('utf8'))
        fileOut.close()
              
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
        return 0, deviceDict
        
    def downloadXML(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
                
        mapResult, mapDict = self.downloadMapXML()
        if mapResult == 0:
            eviceResult, deviceDict = self.downloadDeviceXML(mapDict)           
            if eviceResult == 0:
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
                return 0, deviceDict, mapDict
            else:
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
                return 1, 1, 1
        else:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 1, 1, 1  
    
    def downloadMap(self, mapId, mapDict, deviceDict):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        
        coords = []
        try:
            currentMap = mapDict[mapId]
        except KeyError as e:
            self.logger.error("sessionNo=\"%i\" action=\"Downloading Maps\" message=\"Invalid Map ID\" id=\"%s\"", self.sessionNo, mapId)
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            return 0

        if currentMap != None:
            mapFilePath = join(FILEPATHS['imageRoot'], currentMap.mapImage())
            mapFile = self.fileHandler.accessPath(mapFilePath, 'wb')
            try:
                mapImage = self.httpConnector.getMapImage(mapId).read()
            except HTTPError as e:
                self.logger.error("sessionNo=\"%i\" action=\"Downloading Map Image\" message=\"Error: HTTP Error %s\"", self.sessionNo, str(e.code))
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
            except IOError as e:
                self.logger.error("sessionNo=\"%i\" action=\"Downloading Map Image\" message=\"Error: Unable to connect - %s\"", self.sessionNo, str(format(e)))
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
            except Exception as e:
                self.logger.error("sessionNo=\"%i\" action=\"Downloading Map Image\" message=\"Error: Unexpected Error - %s\"", self.sessionNo, str(format(e)))
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
            else:
                mapFile.write(mapImage)
                mapFile.close()
                
            imGlobals.globalMapId = mapId
            self.logger.debug("HP-DEBUG: downloadMap4() switching to map =\"%s\"", imGlobals.globalMapId)
            mapFileBgPath = join(FILEPATHS['imageRoot'], currentMap.mapBgImage())
            mapFileBg = self.fileHandler.accessPath(mapFileBgPath, 'wb')
            try:
                mapBgImage = self.httpConnector.getMapBgImage(mapId).read()
            except HTTPError as e:
                self.logger.error("sessionNo=\"%i\" action=\"Downloading Map BG Image\" message=\"Error: HTTP Error %s\"", self.sessionNo, str(e.code))
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
            except IOError as e:
                self.logger.error("sessionNo=\"%i\" action=\"Downloading Map BG Image\" message=\"Error: Unable to connect - %s\"", self.sessionNo, str(format(e)))
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
            except Exception as e:
                self.logger.error("sessionNo=\"%i\" action=\"Downloading Map BG Image\" message=\"Error: Unexpected Error - %s\"", self.sessionNo, str(format(e)))
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
            else:
                mapFileBg.write(mapBgImage)
                mapFileBg.close()
            
            rectExtraction = None
            mapLink = None
            bgDetail = None
            h = HTMLParser.HTMLParser()
            try:
                rawMapHTML = self.httpConnector.getMapHTML(mapId).read()
            except HTTPError as e:
                self.logger.error("sessionNo=\"%i\" action=\"Reading Map Coordinates\" message=\"Error: HTTP Error %s\"", self.sessionNo, str(e.code))
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
            except IOError as e:
                self.logger.error("sessionNo=\"%i\" action=\"Reading Map Coordinates\" message=\"Error: Unable to connect -  %s\"", self.sessionNo, str(format(e)))
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
            except Exception as e:
                self.logger.error("sessionNo=\"%i\" action=\"Reading Map Coordinates\" message=\"Error: Unexpected Error - %s\"", self.sessionNo, str(format(e)))
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
            else:
                try:
                    ImMap = toUnicode(h.unescape(rawMapHTML.decode('iso-8859-1')))
                except Exception as e:
                    self.logger.critical("scriptName=\"%s\" self.sessionNo=\"%i\" action=\"Map HTML Parse Error\" message=\"%s\"", sys.argv[0], self.sessionNo, str(format(e)))
                    raise
                rectExtraction = re.findall(r'COORDS="(\d+,\d+,\d+,\d+)" HREF="/[^/]+/[^/]+/(\w+)/!(\w+).html', ImMap)
                mapLink = re.findall(r'COORDS="(\d+,\d+,\d+,\d+)" HREF="/(\w+)">', ImMap)
                bgDetail = re.findall(r'<div id="cssstylemapbg".*>top:(\d+);\s*left:(\d+);</div>', ImMap)
            
            if bgDetail:
                for ext_data in bgDetail:
                    (topOffset, leftOffset) = ext_data
                    currentMap.bgImage = True
                    currentMap.bgTop = topOffset
                    currentMap.bgLeft = leftOffset
            else:
                currentMap.bgTop = '0'
                currentMap.bgLeft = '0'
            
            if mapLink:
                self.logger.debug("sessionNo=\"%i\" action=\"Reading Map Coordinates\" message=\"Found map link\"", self.sessionNo)
                for extracted_data in mapLink:
                    (coordinates, mapLinkId) = extracted_data
                try:
                    #mapLinkName = 
                    re.sub(r'\s', '_', mapDict[mapLinkId].mapName)
                except KeyError as e:
                    self.logger.error("sessionNo=\"%i\" action=\"Map Link Parse Operation\" message=\"Error: Map for map link does not exist - %s\"", self.sessionNo, str(format(e)))
                else:
                    coords.append("<AREA SHAPE=RECT COORDS=\"" + coordinates + "\" HREF=\"" + FILEPATHS['linkRoot'] + mapDict[mapLinkId].xmlPath()[:-4] + "\"/>\n")
    
            if rectExtraction and (deviceDict !=None) and (len(deviceDict)>0):
                for extracted_data in rectExtraction:
                    (coordinates, imid, devtype) = extracted_data
                    if devtype == "device":
                        try:
                            hrefUrl = join(FILEPATHS['linkRoot'], deviceDict[imid].dashboardPath()[:-4])                        
                        except KeyError as e:
                            self.logger.error("sessionNo=\"%i\" action=\"Device Link Parse Operation\" message=\"Error: Device Dashboard does not exist - %s\"", self.sessionNo, str(format(e)))
                        else:
                            coords.append("<AREA SHAPE=RECT COORDS=\"" + coordinates + "\" HREF=\"" + hrefUrl + "\"/>\n")
                            
            
            splunkhtm = ''.join(coords)
            timeString = toUnicode(ctime())
			
            if self.timeoutInSeconds is not None:
                timeout = unicode(self.timeoutInSeconds)
            else:
                timeout = u'20'
            
            outputUnicode = (u'<script>setInterval(refreshPage,' + timeout + u' * 1000); function refreshPage(){window.location.reload(true);}</script>' 
                 + u'<H2>' + escape(currentMap.mapName) + u' - Updated ' + timeString 
                 + '</H2><div class="mapInclude"><MAP NAME="imap" id="imap">\n'
                 + splunkhtm + u'\n'
                 + u'<br/><br/><div style="position:relative">' 
                 + u'<img id="mapbg" style="position:absolute; margin-left:0px; margin-top:0px; left:' + currentMap.bgLeft + 'px; top:' 
                 + currentMap.bgTop + 'px;" src="../../static/app/InterMapper/images/' + currentMap.mapBgImage() + u'">\n' 
                 + u'<img id="mapfg" style="position:relative; left:0px; top:0px;" src="../../static/app/InterMapper/images/' 
                 + currentMap.mapImage() + u'" border="0" usemap="#imap">\n' 
                 + u'</div></div></div>')
                            
            mapHtmlPath = join(FILEPATHS['outputHtml'], currentMap.htmlPath())
            fileOut = self.fileHandler.accessPath(mapHtmlPath, 'w')
            fileOut.write(outputUnicode.encode('utf8'))
            fileOut.close()
            
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
    
    def downloadMaps(self, mapDict, deviceDict):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
      
        for mapId in mapDict.keys():
            self.downloadMap(mapId, mapDict, deviceDict)
        
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
        
## end class ImDownloader
