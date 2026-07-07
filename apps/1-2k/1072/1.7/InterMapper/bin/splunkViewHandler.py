
# InterMapper for Splunk App - class to handle Splunk dashboard creation, modification and deletion

import logging
from os.path import join
from xml.sax.saxutils import escape
from imUtils import logMethodEntry, logMethodExit, escapeApos, mapXMLPathToImMap, restReloadViews, toUnicode, FILEPATHS

class SplunkViewHandler(object):
    sessionNo = None
    exitHandler = None
    fileHandler = None
    defaultTemplate = None
    logger = None
    scrRuntime = None
    sessionKey = None
    
    def __init__(self, exitHandler, fileHandler, sessionKey=None, sessionNo= -1, logLevel=logging.INFO, scrRuntime=False):
        self.sessionNo = sessionNo
        self.exitHandler = exitHandler
        self.fileHandler = fileHandler
        self.defaultTemplate = join(FILEPATHS['defaultDir'], "uc.imtemp")
        self.logger = logging.getLogger('splunk.apps.intermapper.splunkviewhandler')
        self.logger.setLevel(logLevel)
        self.scrRuntime = scrRuntime
        self.sessionKey = sessionKey
    
    ### Change Detection ###
    
    def cleanUpDashboards(self, deviceDict, existingDashs, oldDeviceDict):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
    
        if existingDashs:
            firstRun = "False"
        else:
            firstRun = "True"
    
        self.logger.debug("sessionNo=\"%i\" action=\"Cleanup Dashboards First run\" message=\"%s\"", self.sessionNo, firstRun)
    
        currentDashs = []
        toDelete = []
        toGenerate = []
    
        if firstRun == "True":
            for (imid, currentDevice) in deviceDict.items():
                currentDashs.append(currentDevice.dashboardPath())
                toGenerate.append(imid)
                # self.logger.debug("sessionNo=\"%i\" action=\"Checking for dashboards to generate\" message=\"Need to generate - %s\"", self.sessionNo, imid.encode('utf8'))
        else:
            for (imid, currentDevice) in deviceDict.items():
                currentDashPath = currentDevice.dashboardPath()
                currentDashs.append(currentDashPath)
                try:
                    existingDashs.index(currentDashPath)
                except ValueError:
                    toGenerate.append(imid)
                    # self.logger.debug("sessionNo=\"%i\" action=\"Checking for dashboards to generate\" message=\"Need to generate - %s\"", self.sessionNo, imid.encode('utf8'))
                else:
                    # test oldDeviceDict for update
                    if (imid in oldDeviceDict):			# the new imid is in the old diectionary
                        oldDevice = oldDeviceDict[imid]
                        if (currentDevice.deviceName != oldDevice.deviceName):
                            #self.logger.debug("sessionNo=\"%i\" action=\"Checking for dashboards to generate\" message=\"Device Name updated; need to regenerate - %s\" old=\"%s\" new=\"%s\"", self.sessionNo, imid.encode('utf8'), oldDevice.deviceName.encode('utf8'), currentDevice.deviceName.encode('utf8'))
                            toDelete.append(currentDashPath)
                            toGenerate.append(imid)
                        elif (currentDevice.deviceIP != oldDevice.deviceIP):
                            #self.logger.debug("sessionNo=\"%i\" action=\"Checking for dashboards to generate\" message=\"Device IP updated; need to regenerate - %s\" old=\"%s\" new=\"%s\"", self.sessionNo, imid.encode('utf8'), oldDevice.deviceIP.encode('utf8'), currentDevice.deviceIP.encode('utf8'))
                            toDelete.append(currentDashPath)
                            toGenerate.append(imid)
#                        elif (currentDevice.deviceTemplate != oldDevice.deviceTemplate):
#                            # self.logger.debug("sessionNo=\"%i\" action=\"Checking for dashboards to generate\" message=\"Device Template updated; need to regenerate - %s\" old=\"%s\" new=\"%s\"", self.sessionNo, imid.encode('utf8'), oldDevice.deviceTemplate.encode('utf8'), currentDevice.deviceTemplate.encode('utf8'))
#                            toDelete.append(currentDashPath)
#                            toGenerate.append(imid)
                        #else:
                        #    self.logger.debug("sessionNo=\"%i\" action=\"Checking for dashboards to generate\" message=\"Don't need to generate - %s\"", self.sessionNo, imid.encode('utf8'))
                    else:
                        toDelete.append(currentDashPath)
                        toGenerate.append(imid)
                        #self.logger.error("sessionNo=\"%i\" action=\"Checking for dashboards to generate\" message=\"Existing dashboard not in deviceTable.csv, regenerating: - %s\"", self.sessionNo, imid.encode('utf8'))
    
            for fileName in existingDashs:
                try:
                    currentDashs.index(fileName)
                except ValueError:
                    toDelete.append(fileName)
                    self.logger.debug("sessionNo=\"%i\" action=\"Checking for dashboards to delete\" message=\"Need to delete - %s\"", self.sessionNo, fileName)
                else:
                    self.logger.debug("sessionNo=\"%i\" action=\"Checking for dashboards to delete\" message=\"Don't need to delete - %s\"", self.sessionNo, fileName)
      
        if toDelete: 
            self.deleteDashboards(toDelete)
        if toGenerate:    
            self.generateDashboards(deviceDict, toGenerate)
      
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
    
    
    def cleanUpMaps(self, mapDict, existingMaps, oldMapDict):
        
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)    
        if existingMaps:
            firstRun = False
        else:
            firstRun = True
    
        self.logger.debug("sessionNo=\"%i\" action=\"Cleanup Maps First run\" message=\"%s\"", self.sessionNo, str(firstRun))
    
        currentMaps = []
        toDelete = []
        toGenerate = []
        defaultFound = False
    
        if firstRun:
            for (mid, currentMap) in mapDict.items():
                if currentMap.defaultMap:
                    defaultFound = True            
                currentMaps.append(currentMap.xmlPath())
                toGenerate.append(mid)               
                self.logger.debug("sessionNo=\"%i\" action=\"Checking for maps to generate\" message=\"Need to generate - %s\"", self.sessionNo, mid.encode('utf8'))
        else:
            for (mid, currentMap) in mapDict.items():
                if currentMap.defaultMap:
                    defaultFound = True
                currentMapXmlPath = currentMap.xmlPath()
                currentMaps.append(currentMapXmlPath)
                try:
                    existingMaps.index(currentMapXmlPath)
                except ValueError:
                    toGenerate.append(mid)
                    self.logger.debug("sessionNo=\"%i\" action=\"Checking for maps to generate\" message=\"Need to generate - %s\"", self.sessionNo, mid.encode('utf8'))
                else:
                    # test oldMapDict for update
                    if (mid in oldMapDict):
                        oldMap = oldMapDict[mid]
                        if (currentMap.mapName != oldMap.mapName):
                            self.logger.debug("sessionNo=\"%i\" action=\"Checking for maps to generate\" message=\"Map Name updated; need to regenerate - %s\" old=\"%s\" new=\"%s\"", self.sessionNo, mid.encode('utf8'), oldMap.mapName.encode('utf8'), currentMap.mapName.encode('utf8'))
                            toDelete.append(currentMapXmlPath)
                            toGenerate.append(mid)
                        elif (currentMap.mapLayer != oldMap.mapLayer):
                            self.logger.debug("sessionNo=\"%i\" action=\"Checking for maps to generate\" message=\"Layer 2 toggled; need to regenerate - %s\" old=\"%s\" new=\"%s\"", self.sessionNo, mid.encode('utf8'), oldMap.mapLayer.encode('utf8'), currentMap.mapLayer.encode('utf8'))
                            toDelete.append(currentMapXmlPath)
                            toGenerate.append(mid)
                        elif currentMap.defaultMap:
                            # generate the default map no matter what in case we need to replace a stale error page
                            self.logger.debug("sessionNo=\"%i\" action=\"Checking for maps to generate\" message=\"Default map; need to regenerate - %s\" old=\"%s\" new=\"%s\"", self.sessionNo, mid.encode('utf8'), oldMap.mapLayer.encode('utf8'), currentMap.mapLayer.encode('utf8'))
                            toDelete.append(currentMapXmlPath)
                            toGenerate.append(mid)
                        else:
                            self.logger.debug("sessionNo=\"%i\" action=\"Checking for maps to generate\" message=\"Don't need to generate - %s\"", self.sessionNo, mid.encode('utf8'))
                    else:
                        toDelete.append(mid)
                        toGenerate.append(mid)
                        self.logger.error("sessionNo=\"%i\" action=\"Checking for maps to generate\" message=\"Existing map not in mapTable.csv, regenerating: - %s\"", self.sessionNo, mid.encode('utf8'))
    
            for fileName in existingMaps:
                try:
                    currentMaps.index(fileName)
                except ValueError:
                    toDelete.append(fileName)
                    self.logger.debug("sessionNo=\"%i\" action=\"Checking for maps to delete\" message=\"Need to delete - %s\"", self.sessionNo, fileName)
                else:
                    self.logger.debug("sessionNo=\"%i\" action=\"Checking for maps to delete\" message=\"Don't need to delete - %s\"", self.sessionNo, fileName)
    
        if toDelete:
            self.deleteMaps(toDelete)
      
        if toGenerate:
            self.generateMapStaticFiles(mapDict, toGenerate)
            
        if not defaultFound:
            self.generateDefaultMapNotFoundHtml()
    
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
    
    ### View Deletion ###
    
    def deleteDashboards(self, toDelete):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        for name in toDelete:
            dest = join(FILEPATHS['viewRoot'], name)
            self.fileHandler.accessPath(dest, 'd')
        if self.sessionKey != None:
            restReloadViews(self.sessionNo, self.sessionKey)
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
    
    def deleteMaps(self, toDelete):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
      
        for name in toDelete:
            imMap = mapXMLPathToImMap(name)
            xmlDest = join(FILEPATHS['viewRoot'], imMap.xmlPath())
            self.fileHandler.accessPath(xmlDest, 'd')
            staticHtmlDest = join(FILEPATHS['outputHtml'], imMap.staticHtmlPath())
            self.fileHandler.accessPath(staticHtmlDest, 'd')
            htmlDest = join(FILEPATHS['outputHtml'], imMap.htmlPath())
            self.fileHandler.accessPath(htmlDest, 'd')
            pngDest = join(FILEPATHS['imageRoot'], imMap.mapImage())
            self.fileHandler.accessPath(pngDest, 'd')
            bgpngDest = join(FILEPATHS['imageRoot'], imMap.mapBgImage())
            self.fileHandler.accessPath(bgpngDest, 'd')
    
        if self.sessionKey != None:
            restReloadViews(self.sessionNo, self.sessionKey)
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)

    ### View Generation ###
    
    def generateDefaultMapNotFoundHtml(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        
        defHtml = join(FILEPATHS['outputHtml'], "immapDefault.html")
        fileOut = open(defHtml, 'w')
        outputUnicode = (u'<H2>Default Map Not Found</H2><META HTTP-EQUIV="REFRESH" CONTENT="10"/>'
                         + u'<center><H3>The default map specified during setup cannot be located.<H3></center><br/>'
                         + u'<center><H3>Please check the spelling and ensure you have access to the map.<H3></center>'
                         + u'<center><H3><a href="/manager/InterMapper/apps/local/InterMapper/setup?action=edit">Click here to view configuration details</a><H3></center>') 
        fileOut.write(outputUnicode.encode('utf8'))
        fileOut.close()
        
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
    
    def generateMapStaticFiles(self, mapDict, toGenerate):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        
        for mid in toGenerate:
            currentMap = mapDict[mid]
            # generate XML file
            xmlDest = join(FILEPATHS['viewRoot'], currentMap.xmlPath())
            outf = self.fileHandler.accessPath(xmlDest, 'w')
            xmlOutput = self.loadMapTemplate(currentMap, FILEPATHS['mapXmlTemplate'])
            outf.write(xmlOutput.encode('utf8'))
            outf.close()
            # generate initial HTML file
            htmlDest = join(FILEPATHS['outputHtml'], currentMap.staticHtmlPath())
            outf = self.fileHandler.accessPath(htmlDest, 'w')
            htmlOutput = self.loadMapTemplate(currentMap, FILEPATHS['mapHtmlTemplate'])
            outf.write(htmlOutput.encode('utf8'))
            outf.close()
            
            if currentMap.defaultMap:
                self.logger.debug("sessionNo=\"%i\" action=\"Found default map\" mapname=\"%s\"", self.sessionNo, currentMap.mapName)
                defaultHtmlPath = join(FILEPATHS['outputHtml'], "immapDefault.html")
                fileOut = self.fileHandler.accessPath(defaultHtmlPath, 'w')
                fileOut.write(htmlOutput.encode('utf8'))
                fileOut.close()
            else:
                self.logger.debug("sessionNo=\"%i\" message=\"not default map\" mapname=\"%s\"", self.sessionNo, currentMap.mapName)
        
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
      
    def generateDashboards(self, deviceDict, toGenerate):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        
        for imid in toGenerate:
            currentDevice = deviceDict[imid]
            if currentDevice is not None:
                dest = join(FILEPATHS['viewRoot'], currentDevice.dashboardPath())
                if currentDevice.type == "device":
                    outf = self.fileHandler.accessPath(dest, 'w')
                    if outf is not None:
                        outf.write(self.loadDeviceTemplate(currentDevice).encode('utf8'))
                        outf.close()
                    else:
                        self.logger.debug("HP DEBUG: could not open file for write: \"%s\"\n", dest)
            else:
                self.logger.debug("HP DEBUG: found invalid imid =\"%s\"\n", imid)
                
        if self.sessionKey != None:
            restReloadViews(self.sessionNo, self.sessionKey)
        logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)

    def loadMapTemplate(self, currentMap, templatePath):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        substVars = {'mapName':  escapeApos(escape(currentMap.mapName)),
                     'htmlPath': escape(currentMap.htmlPath()),
                     'staticHtmlPath': escape(currentMap.staticHtmlPath()),
                     'mapId': escape(currentMap.mapId) } #xml escape
        template = None
        try:
            template = toUnicode(open(templatePath, 'r').read()) % substVars
        except:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            raise
        if (template != None):
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
            return template
        
    def loadDeviceTemplate(self, device):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)

        searchString = 'device_imid="' + device.deviceIMID + '"'

#        searchString = '\"' + device.deviceName + '\"'
#        if device.deviceHost != None and device.deviceHost != '':
#            searchString = searchString + ' AND \"' + device.deviceHost + '\"'
#        if device.deviceSysName != None and device.deviceSysName != '':
#            searchString = searchString + ' AND \"' + device.deviceSysName + '\"'
#        if device.deviceNetBios != None and device.deviceNetBios != '':
#            searchString = searchString + ' AND \"' + device.deviceNetBios + '\"'
#        searchString = searchString + ' AND \"' + device.deviceIMID + '\"'
		
        substVars = {'deviceLabel': escape(device.deviceName),
                     'deviceIp': escape(device.deviceIP),
                     'deviceId': escape(device.deviceIMID),
                     'searchString': escape(searchString)} #xml escape
        template = None
        try:
            # use only default template
            template = toUnicode(open(self.defaultTemplate, 'r').read()) % substVars
        except:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            raise
    
        if (template != None):
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
            return template

## end class SplunkViewHandler
