# InterMapper for Splunk App - Handler for Configure App screen

import splunk.admin as admin
import ConfigParser
from os.path import dirname, join
from base64 import b64encode#, b64decode
import logging #@UnusedImport
import logging.handlers

############# Enable debug mode below #############
debug = 1
###################################################
# set up logging
logDirectory = join(dirname(__file__), '..', 'local')
if not os.path.exists(logDirectory):
    try:
       os.makedirs(logDirectory)
    except OSError as e:
        if e.errno != errno.EEXIST:
           raise
if debug:
    globalLogLevel = logging.DEBUG
    globalLogFileName = join(logDirectory, 'imConfigDebug.log')   
else:
    globalLogLevel = logging.INFO
    globalLogFileName = join(logDirectory, 'imConfig.log')

rootLogger = logging.getLogger('splunk.apps.intermapper')
rootLogger.setLevel(globalLogLevel)
handler = logging.handlers.RotatingFileHandler(filename=globalLogFileName, mode='a', maxBytes=1000000, backupCount=5)
handler.setFormatter(logging.Formatter('%(asctime)s log_level=%(levelname)s %(message)s'))
rootLogger.addHandler(handler)

class ConfigApp(admin.MConfigHandler):
    requiredArgs = ['defaultMapName', 'serverUrl', 'sslRequired']
    standardOptArgs = ['serverPort', 'timeoutInSeconds']
    specialOptArgs = ['username', 'password']
    standardArgs = requiredArgs + standardOptArgs
    optArgs = standardOptArgs + specialOptArgs

    def setup(self):
        rootLogger.debug("Setup Called")
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in self.requiredArgs:
                self.supportedArgs.addReqArg(arg)
            for arg in self.optArgs:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        rootLogger.debug("List Called")
        confDict = self.readConf("settings")
        portFromUrl = False
        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key == 'serverUrl':
                        if val in [None, '']:
                            val = ''
                            confInfo[stanza].append(key, val)
                        else:
                            parts = val.split(':')
                            if len(parts) == 2:
                                rootLogger.debug("Splitting serverUrl - %s", val)
                                confInfo[stanza].append('serverUrl', parts[0])
                                confInfo[stanza].append('serverPort', parts[1])
                                portFromUrl = True
                            else:
                                rootLogger.debug("Not splitting serverUrl - %s", val)
                                confInfo[stanza].append(key, val)
                    elif key == 'serverPort' and portFromUrl:
                        rootLogger.info('Ignoring clobbered serverPort - %s', val)
                    else:
                        if key in self.standardArgs and val in [None, '']:
                            val = ''
                        confInfo[stanza].append(key, val)
                confInfo[stanza].append('username', '')
                confInfo[stanza].append('password', '')

    # version to handle username and password retrieval; doesn't fill "confirm password" box
#    def handleList(self, confInfo):
#        confDict = self.readConf("settings")
#        if None != confDict:
#            for stanza, settings in confDict.items():
#                for key, val in settings.items():
#                    if key == 'auth':
#                        if val in [None, '']:
#                            rootLogger.debug("No auth string saved")
#                            confInfo[stanza].append('username', '')
#                            confInfo[stanza].append('password', '')
#                        else:
#                            auth = b64decode(val).split(':', 1)
#                            if len(auth) == 2:
#                                confInfo[stanza].append('username', auth[0])
#                                confInfo[stanza].append('password', auth[1])
#                            else:
#                                rootLogger.error("Problem splitting auth string - %s", auth)
#                                confInfo[stanza].append('username', '')
#                                confInfo[stanza].append('password', '')
#                    elif key == 'serverUrl':
#                        if val in [None, '']:
#                            val = ''
#                            confInfo[stanza].append(key, val)
#                        else:
#                            parts = val.split(':')
#                            if len(parts) == 2:
#                                rootLogger.debug("Trying to split serverUrl")
#                                confInfo[stanza].append('serverUrl', parts[0])
#                                confInfo[stanza].append('serverPort', parts[1])
#                            else:
#                                rootLogger.debug("Not trying to split serverUrl")
#                                confInfo[stanza].append(key, val)
#                    else:
#                        if key in self.standardArgs and val in [None, '']:
#                            val = ''
#                        confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo): #@UnusedVariable
        rootLogger.debug("Edit Called")
        outputHtml = join(dirname(__file__), '..', 'appserver', 'static', '')
        fileOut = open(outputHtml + "immapDefault.html", 'w')
        fileOut.write('<center><H2>Script generating dashboards - This process can take a few minutes on first run. The screen may refresh multiple times while this executes.</H2><BR/><META HTTP-EQUIV="REFRESH" CONTENT="20"/></center>\n')
        fileOut.write('<center><img src="../../static/app/InterMapper/images/loading.gif"></img></center>')
        fileOut.close()
        
        settings = self.callerArgs.data

        for arg in self.standardArgs:
            if settings[arg][0] in [None, '']:        
                settings[arg][0] = ''
            rootLogger.debug(arg + " = " + settings[arg][0])
        
        user = settings.pop('username')[0]
        passwd = settings.pop('password')[0] 
        if not(user in [None, ''] or passwd in [None, '']):
            settings['auth'] = b64encode(str(user) + ":" + str(passwd))
        else:
            settings['auth'] = ''
        rootLogger.debug("auth = " + settings['auth'])
    
        localConf_fp = join(dirname(__file__), '..', 'local', 'state.conf')
        localConfig = ConfigParser.ConfigParser()
        localConfig.read(localConf_fp)
        localConfig.set("state", "forceReload", "1")
        configFile = open(localConf_fp, "w")
        localConfig.write(configFile)
    
        self.writeConf('settings', 'imsettings', settings)
        
# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
